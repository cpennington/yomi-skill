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

logger = logging.getLogger(__name__)


def elo_logit(games):
    elo_diff = games.elo_before_1 - games.elo_before_2
    elo_pct_p1_win = 1 / (1 + (-elo_diff / 1135.77).rpow(10))
    return numpy.log(elo_pct_p1_win / (1 - elo_pct_p1_win))


class YomiModel(ABC, BaseEstimator, ClassifierMixin):
    model_name: str
    model_hash: str
    data_: pandas.DataFrame
    inf_data_: arviz.InferenceData

    def __init__(
        self,
        data_dir,
        min_games=0,
        warmup=500,
        samples=1000,
    ):
        self.data_dir = data_dir
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
        self.data_["vmup"] = self.data_.apply(
            lambda r: self.version_mu_index_[
                (r.character_1, r.version_1, r.character_2, r.version_2)
            ],
            axis=1,
        )
        self.data_["non_mirror"] = self.data_.apply(
            lambda r: int(r.character_1 != r.character_2), axis=1
        )
        self.data_["elo_logit"] = elo_logit(self.data_)
        self.data_["skelo_logit"] = logit(self.data_.elo_estimate)
        self.data_["skglicko_logit"] = logit(self.data_.glicko_estimate)
        self.data_["skglicko_pc_logit"] = logit(self.data_.pc_glicko_estimate)

        self.data_["character_ix_1"] = self.data_.character_1.apply(
            self.character_index_.get
        )
        self.data_["character_ix_2"] = self.data_.character_2.apply(
            self.character_index_.get
        )
        self.data_["version_ix_1"] = self.data_.version_1.apply(self.version_index_.get)
        self.data_["version_ix_2"] = self.data_.version_2.apply(self.version_index_.get)
        self.data_["player_ix_1"] = self.data_.player_1.apply(self.player_index_.get)
        self.data_["player_ix_2"] = self.data_.player_2.apply(self.player_index_.get)

    def clear_all_cached_properties(self):
        class_attrs = dir(self.__class__)
        for attr in class_attrs:
            if isinstance(getattr(self.__class__, attr), cached_property) and hasattr(
                self, attr
            ):
                delattr(self, attr)

    @abstractmethod
    def fit(self, X: pandas.DataFrame, y):
        self.clear_all_cached_properties()
        self.data_hash_ = hash(X.values.tobytes())
        self._prep_data(X)
        self.classes_, y = numpy.unique(y, return_inverse=True)
        self.y_ = y

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
    def version_mu_index_(self):
        return dict(
            zip(
                (
                    (row.character_1, row.version_1, row.character_2, row.version_2)
                    for row in self.data_[
                        ["character_1", "version_1", "character_2", "version_2"]
                    ]
                    .drop_duplicates()
                    .itertuples()
                ),
                range(1, 1000),
            )
        )

    @cached_property
    def characters_(self):
        return sorted(
            pandas.concat([self.data_.character_1, self.data_.character_2]).unique()
        )

    @cached_property
    def versions_(self):
        return sorted(
            pandas.concat([self.data_.version_1, self.data_.version_2]).unique()
        )

    @cached_property
    def character_versions_(self):
        return sorted(
            pandas.concat(
                [
                    self.data_[["character_1", "version_1"]].rename(
                        columns={"character_1": "character", "version_1": "version"}
                    ),
                    self.data_[["character_2", "version_2"]].rename(
                        columns={"character_2": "character", "version_2": "version"}
                    ),
                ]
            )
            .drop_duplicates()
            .itertuples(index=False)
        )

    @cached_property
    def character_index_(self):
        return {char: index for index, char in enumerate(self.characters_)}

    @cached_property
    def version_index_(self):
        return {version: index for index, version in enumerate(self.versions_)}

    @cached_property
    def player_tournament_index_(self):
        return dict(
            self.player_tournament_dates_.apply(
                lambda r: ((r.player, r.tournament_name), r.name), axis=1
            ).values
        )

    @cached_property
    def player_tournament_dates_(self):
        p1_games = self.data_[["player_1", "tournament_name", "match_date"]].rename(
            columns={"player_1": "player"}
        )
        p2_games = self.data_[["player_2", "tournament_name", "match_date"]].rename(
            columns={"player_2": "player"}
        )
        return (
            pandas.concat([p1_games, p2_games])
            .groupby(["player", "tournament_name"])
            .match_date.quantile(0.5)
            .reset_index()
            .sort_values(["match_date", "player"])
            .reset_index(drop=True)
        )

    @cached_property
    def tournament_index_(self):
        ordered_tournaments = (
            self.data_.groupby("tournament_name")
            .match_date.quantile(0.5)
            .reset_index()
            .sort_values("match_date")
            .tournament_name
        )
        return dict(zip(ordered_tournaments, range(1, 1000)))

    def cachepath_(
        self,
        *,
        subdirs: List[str] | None = None,
        extension: str | None = None,
        fold: int | None = None,
    ):
        path = [
            self.data_dir,
            f"{self.model_name}-{self.model_hash[:6]}",
            f"warmup-{self.warmup}",
            f"samples-{self.samples}",
            f"data-{self.data_hash_}",
        ]
        if self.min_games > 0:
            path.append(f"min-games-{self.min_games}")
        if subdirs:
            path.extend(subdirs)
        if extension:
            path[-1] = f"{path[-1]}.{extension}"

        return os.path.join(*path)

    def fit_filename_(self):
        return self.cachepath_()

    def parquet_filename_(self):
        return self.cachepath_(extension="parquet")

    def netcdf_filename_(self):
        return self.cachepath_(extension="netcdf")

    def fill_untrained_players(self, mean_skill, X):
        untrained_players = (set(X.player_1) | set(X.player_2)) - set(
            mean_skill.coords["player"].values
        )
        if self.min_games_player_:
            untrained_data = numpy.array(
                [mean_skill.sel(player=self.min_games_player_).values]
                * len(untrained_players)
            )
        else:
            untrained_data = numpy.full(
                (len(mean_skill.coords["character"]), len(untrained_players)),
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
