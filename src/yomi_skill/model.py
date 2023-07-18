import logging
import os
from abc import ABC, abstractmethod
from functools import cached_property
from typing import List

import arviz
import numpy
import pandas
import xarray
from scipy.special import logit
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import scale, FunctionTransformer

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
        result.loc[
            result.player_1.isin(not_enough_played), "player_1"
        ] = min_games_player_

        result.loc[result.player_2.isin(not_enough_played), "min_games_player_2"] = True
        result.loc[
            result.player_2.isin(not_enough_played), "player_2"
        ] = min_games_player_

    return result


min_games_transformer = FunctionTransformer(_transform_min_games)


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

    def _prep_data(self, games: pandas.DataFrame):
        self.data_ = games.copy()
        self.data_["player_1_orig"] = self.data_.player_1
        self.data_["player_2_orig"] = self.data_.player_2
        if self.min_games > 0:
            games_played = (
                pandas.concat([self.data_.player_1, self.data_.player_2])
                .rename("player")
                .to_frame()
                .groupby("player")
                .size()
                .rename("count")
                .reset_index()
            )
            not_enough_played = games_played[
                games_played["count"] < self.min_games
            ].player

            self.data_ = self.data_.astype({"player_1": str, "player_2": str})

            self.min_games_player_ = f"< {self.min_games} games"

            self.data_.loc[
                self.data_.player_1.isin(not_enough_played), "player_1"
            ] = self.min_games_player_
            self.data_.loc[
                self.data_.player_2.isin(not_enough_played), "player_2"
            ] = self.min_games_player_
        else:
            self.min_games_player_ = None
        self.data_["player_1"] = self.data_.player_1.astype("category")
        self.data_["player_2"] = self.data_.player_2.astype("category")
        self.data_["mup"] = self.data_.apply(
            lambda r: self.mu_index_[(r.character_1, r.character_2)], axis=1
        )
        self.data_["non_mirror"] = self.data_.apply(
            lambda r: int(r.character_1 != r.character_2), axis=1
        )

        self.data_["character_ix_1"] = self.data_.character_1.apply(
            self.character_index_.get
        ).astype(int)
        self.data_["character_ix_2"] = self.data_.character_2.apply(
            self.character_index_.get
        ).astype(int)
        self.data_["player_ix_1"] = self.data_.player_1.apply(
            self.player_index_.get
        ).astype("int")
        self.data_["player_ix_2"] = self.data_.player_2.apply(
            self.player_index_.get
        ).astype("int")

    def clear_all_cached_properties(self):
        class_attrs = dir(self.__class__)
        for attr in class_attrs:
            if (
                isinstance(getattr(self.__class__, attr), cached_property)
                and attr in self.__dict__
            ):
                delattr(self, attr)

    @abstractmethod
    def fit(self, X: pandas.DataFrame, y, sample_weight=None) -> "YomiModel":
        self.clear_all_cached_properties()
        self.sample_weight_ = sample_weight
        self.data_hash_ = hash(X.values.tobytes())
        self._prep_data(X)
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

    @cached_property
    def players_(self):
        unique_players = pandas.concat(
            [self.data_.player_1, self.data_.player_2]
        ).unique()
        return sorted(unique_players)

    @cached_property
    def player_index_(self):
        return {player: index for index, player in enumerate(self.players_)}

    @cached_property
    def mu_list_(self):
        return [
            (c1, c2) for c1 in self.characters_ for c2 in self.characters_ if c1 <= c2
        ]

    @cached_property
    def mu_index_(self):
        return {(c1, c2): index for index, (c1, c2) in enumerate(self.mu_list_)}

    @cached_property
    def characters_(self):
        return sorted(
            pandas.concat([self.data_.character_1, self.data_.character_2]).unique()
        )

    @cached_property
    def character_index_(self):
        return {char: index for index, char in enumerate(self.characters_)}

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
