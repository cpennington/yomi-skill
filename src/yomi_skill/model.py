import logging
import os
from abc import ABC, abstractmethod, abstractclassmethod
from functools import cached_property
from typing import List

import arviz
import numpy
import pandas
import xarray
from scipy.special import logit
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import scale, FunctionTransformer
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def min_max_scale(series):
    return (series - series.min()) / (series.max() - series.min())


def z_score_scale(series):
    return (series - series.mean()) / series.std()


def weight_by(games, key):
    # elo_threshold = pandas.concat([hist_games.elo_1, hist_games.elo_2]).quantile(0.9)
    # hist_games["has_high_skill"] = (hist_games.elo_1 > elo_threshold) | (
    #     hist_games.elo_2 > elo_threshold
    # )
    # hist_games["has_low_skill"] = (hist_games.elo_1 <= elo_threshold) | (
    #     hist_games.elo_2 <= elo_threshold
    # )
    scaled_key_1 = games[f"scaled_{key}_1"] = z_score_scale(games[f"{key}_1"])
    scaled_key_2 = games[f"scaled_{key}_2"] = z_score_scale(games[f"{key}_2"])
    max_key = pandas.concat([scaled_key_1, scaled_key_2]).max()
    diff = games[f"{key}_diff_norm"] = z_score_scale(
        -(scaled_key_1 - scaled_key_2).abs()
    )
    max_1 = games[f"{key}_max_norm_1"] = z_score_scale(((scaled_key_1 - max_key)))
    max_2 = games[f"{key}_max_norm_2"] = z_score_scale(((scaled_key_2 - max_key)))
    weight = min_max_scale(diff + max_1 + max_2)
    games[f"{key}_weight"] = len(games) / weight.sum() * weight
    return games


def _transform_min_games(X, min_games=0):
    logger.info("Starting _transform_min_games")
    result = pandas.DataFrame(
        {
            "player_1_orig": X.player_1,
            "player_2_orig": X.player_2,
            "player_1": X.player_1,
            "player_2": X.player_2,
            "min_games_player_1": False,
            "min_games_player_2": False,
        }
    )

    if min_games > 0:
        games_played = (
            pandas.concat([X.player_1, X.player_2])
            .rename("player")
            .to_frame()
            .groupby("player")
            .size()
            .rename("count")
            .reset_index()
        )
        not_enough_played = games_played[games_played["count"] < min_games].player

        result = X.astype({"player_1": str, "player_2": str})

        min_games_player_ = f"< {min_games} games"

        result.loc[result.player_1.isin(not_enough_played), "min_games_player_1"] = True
        result.loc[result.player_1.isin(not_enough_played), "player_1"] = (
            min_games_player_
        )

        result.loc[result.player_2.isin(not_enough_played), "min_games_player_2"] = True
        result.loc[result.player_2.isin(not_enough_played), "player_2"] = (
            min_games_player_
        )

    logger.info("Ending _transform_min_games")
    return result.astype({"player_1": "category", "player_2": "category"})


min_games_transformer = FunctionTransformer(_transform_min_games)


def _transform_matchup(X):
    logger.info("Starting _transform_matchup")
    characters = X.character_1.dtype.categories.values
    mu_list = [
        f"{c1}-{c2}"
        for (o1, c1) in enumerate(characters)
        for (o2, c2) in enumerate(characters)
        if o1 <= o2
    ]
    df = pandas.DataFrame(
        {
            "mup": X[["character_1", "character_2"]]
            .agg("-".join, axis=1)
            .astype(pandas.api.types.CategoricalDtype(mu_list, ordered=True)),
            "character_1": X.character_1,
            "character_2": X.character_2,
            "non_mirror": (X.character_1 != X.character_2).astype(int),
        }
    )
    logger.info("Ending _transform_matchup")
    return df


matchup_transformer = FunctionTransformer(_transform_matchup)


def _transform_gem_effect(X):
    logger.info("Starting _transform_gem_effect")
    characters = X.character_1.dtype.categories.values
    gems = X.gem_1.dtype.categories.values
    print(characters, gems)
    with_gem_list = [f"{c}-{g}" for c in characters for g in gems]
    against_gem_list = [f"{g}-{c}" for c in characters for g in gems]
    print(X[["character_1", "gem_1"]])
    df = pandas.DataFrame(
        {
            "with_gem_1": X[["character_1", "gem_1"]]
            .agg("-".join, axis=1)
            .astype(pandas.api.types.CategoricalDtype(with_gem_list, ordered=True)),
            "with_gem_2": X[["character_2", "gem_2"]]
            .agg("-".join, axis=1)
            .astype(pandas.api.types.CategoricalDtype(with_gem_list, ordered=True)),
            "against_gem_1": X[["gem_1", "character_2"]]
            .agg("-".join, axis=1)
            .astype(pandas.api.types.CategoricalDtype(against_gem_list, ordered=True)),
            "against_gem_2": X[["gem_2", "character_1"]]
            .agg("-".join, axis=1)
            .astype(pandas.api.types.CategoricalDtype(against_gem_list, ordered=True)),
            "gem_1": X.gem_1,
            "gem_2": X.gem_2,
            "character_1": X.character_1,
            "character_2": X.character_2,
        }
    )
    logger.info("Ending _transform_gem_effect")
    return df


gem_effect_transformer = FunctionTransformer(_transform_gem_effect)


def _render(X):
    return pandas.DataFrame(
        {"match_date": X.match_date, "win": X.win, "public": X.public}
    )


render_transformer = FunctionTransformer(_render)


def _dynamic_period_grouper(X, threshold, field_prefix):
    current_period = None
    current_idx = 0

    result = pandas.DataFrame({}, index=X.index)

    for date, games in X.resample("1D", label="right", on="match_date"):
        if current_period is None:
            current_period = games
        else:
            current_period = pandas.concat([current_period, games])

        player_counts = pandas.concat(
            [current_period[f"{field_prefix}_1"], current_period[f"{field_prefix}_2"]]
        ).value_counts()
        played = player_counts[player_counts > 0]
        games_played = played.mean()
        result.loc[games.index, f"period_idx"] = current_idx
        if games_played > threshold:
            current_idx += 1
            current_period = None
    return result


dynamic_period_transformer = FunctionTransformer(_dynamic_period_grouper)


class YomiModel(ABC, BaseEstimator, ClassifierMixin):
    model_name: str
    model_hash: str
    data_: pandas.DataFrame
    inf_data_: arviz.InferenceData
    weight_key: str

    def __init__(
        self,
        min_games=0,
        warmup=500,
        samples=1000,
    ):
        self.min_games = min_games
        self.warmup = warmup
        self.samples = samples

    def clear_all_cached_properties(self):
        class_attrs = dir(self.__class__)
        for attr in class_attrs:
            if (
                isinstance(getattr(self.__class__, attr), cached_property)
                and attr in self.__dict__
            ):
                delattr(self, attr)

    @abstractclassmethod
    def pipeline(cls, **kwargs) -> Pipeline: ...

    @abstractmethod
    def fit(self, X: pandas.DataFrame, y, sample_weight=None) -> "YomiModel":
        self.clear_all_cached_properties()
        self.sample_weight_ = sample_weight
        self.data_ = X
        self.classes_, y = numpy.unique(y, return_inverse=True)
        self.y_ = y
        return self

    @abstractmethod
    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        pass

    def predict_proba(self, X):
        prob_a = self.p1_win_chance(X).to_numpy()
        return prob_a

    def predict(self, X):
        return self.p1_win_chance(X)[1] > 0.5

    def fill_untrained_players(self, mean_skill, X):
        untrained_players = (set(X.player_1) | set(X.player_2)) - set(
            mean_skill.coords["player"].values
        )
        if not untrained_players:
            return mean_skill

        if self.min_games_player_:
            untrained_data = numpy.array(
                [mean_skill.sel(player=self.min_games_player_).values]
                * len(untrained_players)
            )
        else:
            untrained_data = numpy.full(
                (len(untrained_players), len(mean_skill.coords["character"])),
                mean_skill.median(),
            )
        untrained_skill = xarray.DataArray(
            untrained_data,
            {
                "player": sorted(untrained_players),
                "character": mean_skill.coords["character"],
            },
            ["player", "character"],
        )
        return xarray.concat([mean_skill, untrained_skill], "player")
