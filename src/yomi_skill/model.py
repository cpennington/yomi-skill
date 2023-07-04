import pandas
import io
import hashlib
import logging
import os
from cmdstanpy import CmdStanModel, from_csv
from arviz.data import InferenceData
import arviz
import xarray
from cached_property import cached_property
import numpy
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class YomiModel:
    def __init__(
        self,
        games,
        data_dir,
        pars,
        min_games=0,
        warmup=500,
        samples=1000,
    ):
        self.games = games
        self.model_name, _ = os.path.splitext(os.path.basename(self.model_filename))
        self.pars = pars
        self.data_dir = data_dir
        self.min_games = min_games
        self.warmup = warmup
        self.samples = samples
        self.games["player_1_orig"] = self.games.player_1
        self.games["player_2_orig"] = self.games.player_2
        if self.min_games > 0:
            games_played = (
                pandas.concat([self.games.player_1, self.games.player_2])
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

            self.games = self.games.astype({"player_1": str, "player_2": str})

            self.min_games_player = f"< {self.min_games} games"

            self.games.loc[
                self.games.player_1.isin(not_enough_played), "player_1"
            ] = self.min_games_player
            self.games.loc[
                self.games.player_2.isin(not_enough_played), "player_2"
            ] = self.min_games_player

    @cached_property
    def model_hash(self):
        with io.open(self.model_filename) as stan_code:
            model_hash = hashlib.md5()
            for chunk in stan_code:
                model_hash.update(chunk.encode("utf-8"))
            model_hash = model_hash.hexdigest()
        return model_hash

    @cached_property
    def player_index(self):
        return dict(
            zip(
                sorted(
                    pandas.concat([self.games.player_1, self.games.player_2]).unique()
                ),
                range(1, 10000),
            )
        )

    @cached_property
    def mu_index(self):
        return dict(
            zip(
                (
                    (c1, c2)
                    for c1 in self.characters
                    for c2 in self.characters
                    if c1 <= c2
                ),
                range(1, 1000),
            )
        )

    @cached_property
    def version_mu_index(self):
        return dict(
            zip(
                (
                    (row.character_1, row.version_1, row.character_2, row.version_2)
                    for row in self.games[
                        ["character_1", "version_1", "character_2", "version_2"]
                    ]
                    .drop_duplicates()
                    .itertuples()
                ),
                range(1, 1000),
            )
        )

    @cached_property
    def characters(self):
        return sorted(
            pandas.concat([self.games.character_1, self.games.character_2]).unique()
        )

    @cached_property
    def versions(self):
        return sorted(
            pandas.concat([self.games.version_1, self.games.version_2]).unique()
        )

    @cached_property
    def character_versions(self):
        return sorted(
            pandas.concat(
                [
                    self.games[["character_1", "version_1"]].rename(
                        columns={"character_1": "character", "version_1": "version"}
                    ),
                    self.games[["character_2", "version_2"]].rename(
                        columns={"character_2": "character", "version_2": "version"}
                    ),
                ]
            )
            .drop_duplicates()
            .itertuples(index=False)
        )

    @cached_property
    def character_index(self):
        return dict(zip(self.characters, range(1, 100)))

    @cached_property
    def version_index(self):
        return dict(zip(self.versions, range(1, 1000)))

    @cached_property
    def player_tournament_index(self):
        return dict(
            self.player_tournament_dates.apply(
                lambda r: ((r.player, r.tournament_name), r.name + 1), axis=1
            ).values
        )

    @cached_property
    def player_tournament_dates(self):
        p1_games = self.games[["player_1", "tournament_name", "match_date"]].rename(
            columns={"player_1": "player"}
        )
        p2_games = self.games[["player_2", "tournament_name", "match_date"]].rename(
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
    def tournament_index(self):
        ordered_tournaments = (
            self.games.groupby("tournament_name")
            .match_date.quantile(0.5)
            .reset_index()
            .sort_values("match_date")
            .tournament_name
        )
        return dict(zip(ordered_tournaments, range(1, 1000)))

    @cached_property
    def input_data(self):
        # for player in self.player_tournament_dates.player.unique():
        #     self.player_tournament_dates.loc[
        #         self.player_tournament_dates.player == player, "previous"
        #     ] = (
        #         [-1]
        #         + list(
        #             self.player_tournament_dates.loc[
        #                 self.player_tournament_dates.player == player
        #             ].index.values
        #         )[:-1]
        #     )

        # tournament_player = [
        #     self.player_index[player]
        #     for ((player, tournament), _) in sorted(
        #         self.player_tournament_index.items(), key=lambda x: x[1]
        #     )
        # ]

        elo_diff = self.games.elo_before_1 - self.games.elo_before_2
        elo_pct_p1_win = 1 / (1 + (-elo_diff / 1135.77).rpow(10))
        elo_logit = numpy.log(elo_pct_p1_win / (1 - elo_pct_p1_win))

        elo_sum = self.games.elo_before_1 + self.games.elo_before_2
        scaled_weights = 0.25 + 1.75 * (elo_sum - elo_sum.min()) / (
            elo_sum.max() - elo_sum.min()
        )
        normalized_weights = scaled_weights / scaled_weights.sum() * len(self.games)

        return {
            # "NPT": len(self.player_tournament_index),
            "NG": len(self.games),
            "NM": len(self.mu_index),
            "NP": len(self.player_index),
            "NC": len(self.characters),
            "NMV": len(self.version_mu_index),
            # "tp": tournament_player,
            "win": self.games.win.to_numpy(int),
            # "pt1": self.games.apply(
            #     lambda r: self.player_tournament_index[(r.player_1, r.tournament_name)],
            #     axis=1,
            # ),
            # "pt2": self.games.apply(
            #     lambda r: self.player_tournament_index[(r.player_2, r.tournament_name)],
            #     axis=1,
            # ),
            "mup": self.games.apply(
                lambda r: self.mu_index[(r.character_1, r.character_2)], axis=1
            ).to_numpy(int),
            "vmup": self.games.apply(
                lambda r: self.version_mu_index[
                    (r.character_1, r.version_1, r.character_2, r.version_2)
                ],
                axis=1,
            ).to_numpy(int),
            "mu_for_v": [
                self.mu_index[(c1, c2)]
                for ((c1, v1, c2, v2), vix) in sorted(
                    self.version_mu_index.items(), key=lambda i: i[1]
                )
            ],
            "non_mirror": self.games.apply(
                lambda r: float(r.character_1 != r.character_2), axis=1
            ).to_numpy(int),
            # "prev_tournament": self.player_tournament_dates.previous.to_numpy(int).apply(
            #     lambda x: x + 1
            # ),
            "char1": self.games.character_1.apply(self.character_index.get).to_numpy(
                int
            ),
            "char2": self.games.character_2.apply(self.character_index.get).to_numpy(
                int
            ),
            "version1": self.games.version_1.apply(self.version_index.get).to_numpy(
                int
            ),
            "version2": self.games.version_2.apply(self.version_index.get).to_numpy(
                int
            ),
            "player1": self.games.player_1.apply(self.player_index.get).to_numpy(int),
            "player2": self.games.player_2.apply(self.player_index.get).to_numpy(int),
            "elo_logit": elo_logit.to_numpy(),
            # Scale so that mininum elo sum gets 0.25 weight, max sum gets 2 weight
            "obs_weights": normalized_weights.to_numpy(),
            # Disable predictions
            "predict": 0,
        }
    
    @cached_property
    def _file_base(self):
        path = [
            self.data_dir,
            f"{self.model_name}-{self.model_hash[:6]}",
            f"warmup-{self.warmup}",
        ]
        if self.min_games > 0:
            path.append(f"min-games-{self.min_games}")
        return os.path.join(*path)

    @cached_property
    def fit_filename(self):
        return f"{self._file_base}"

    @property
    def fit(self):
        try:
            fit = from_csv(self.fit_filename, "sample")
        except:
            logger.info("Unable to load fit, resampling", exc_info=True)
            model = CmdStanModel(
                stan_file=self.model_filename,
            )
            os.makedirs(self.fit_filename, exist_ok=True)
            fit = model.sample(
                data=self.input_data,
                iter_warmup=self.warmup,
                iter_sampling=self.samples,
                chains=4,
                output_dir=self.fit_filename,
            )
            logger.info("Wrote fit to %s", self.fit_filename)

        return fit

    @cached_property
    def parquet_filename(self):
        return f"{self._file_base}.parquet"

    @property
    def sample_dataframe(self):
        try:
            logger.info(f"Loading parquet {self.parquet_filename}")
            fit_results = pandas.read_parquet(self.parquet_filename)
            for par in self.pars:
                assert any(
                    col.startswith(par) for col in fit_results.columns
                ), f"No parameter {par} found in exported data"
        except (FileNotFoundError, AssertionError):
            logger.info("Dataframe loading failed", exc_info=True)
            fit_results = self.fit.draws_pd(vars=self.pars)
            logger.info("Loaded parameters into dataframe")
            os.makedirs(os.path.dirname(self.parquet_filename), exist_ok=True)
            fit_results.to_parquet(self.parquet_filename, compression="gzip")
            logger.info("Wrote fit to parquet %s", self.parquet_filename)
        return fit_results

    @cached_property
    def netcdf_filename(self):
        return f"{self._file_base}.netcdf"

    @property
    def sample_inf_data(self):
        try:
            inf_data = arviz.data.InferenceData.from_netcdf(self.netcdf_filename)
        except FileNotFoundError:
            print("Converting to InferenceData")
            inf_data = arviz.from_pystan(
                posterior=self.fit,
                posterior_predictive="win_hat",
                observed_data="win",
                log_likelihood="log_lik",
                coords={
                    # "player-tournament": [
                    #     f"{player}-{tournament}"
                    #     for ((player, tournament), _) in sorted(
                    #         self.player_tournament_index.items(),
                    #         key=lambda x: x[1],
                    #     )
                    # ],
                    "matchup": [
                        f"{c1}-{c2}"
                        for ((c1, c2), _) in sorted(
                            self.mu_index.items(), key=lambda x: x[1]
                        )
                    ]
                },
                dims={
                    "skill": ["player-tournament"],
                    "skill_adjust": ["player-tournament"],
                    "mu": ["matchup"],
                    "muv": ["matchup"],
                },
            )

            os.makedirs(os.path.dirname(self.netcdf_filename), exist_ok=True)
            inf_data.to_netcdf(self.netcdf_filename)

        return inf_data

    @property
    def summary_dataframe(self):
        path = [
            self.data_dir,
            f"{self.model_name}-{self.model_hash[:6]}",
            f"warmup-{self.warmup}",
        ]
        if self.min_games > 0:
            path.append(f"min-games-{self.min_games}")
        path.append(f"summary-{self.samples}-samples.parquet")
        parquet_filename = os.path.join(*path)
        try:
            logger.info(f"Loading parquet {parquet_filename}")
            summary_results = pandas.read_parquet(parquet_filename)
            for par in self.pars:
                assert any(
                    col.startswith(par) for col in summary_results.columns
                ), f"No parameter {par} found in exported data"
        except (FileNotFoundError, AssertionError):
            logger.info("Dataframe loading failed", exc_info=True)
            summary_results = self.sample_dataframe.agg(["mean", "std"])
            os.makedirs(os.path.dirname(parquet_filename), exist_ok=True)
            summary_results.to_parquet(parquet_filename, compression="gzip")
        return summary_results


def combine_dataset(left, right):
    if left is None and right is None:
        return None

    return xarray.concat([left, right], "draw")


def combine_inf_data(left, right):
    return InferenceData(
        **{
            "posterior": combine_dataset(
                getattr(left, "posterior", None), getattr(right, "posterior", None)
            ),
            "sample_stats": combine_dataset(
                getattr(left, "sample_stats", None),
                getattr(right, "sample_stats", None),
            ),
            "posterior_predictive": combine_dataset(
                getattr(left, "posterior_predictive", None),
                getattr(right, "posterior_predictive", None),
            ),
            "prior": combine_dataset(
                getattr(left, "prior", None), getattr(right, "prior", None)
            ),
            "sample_stats_prior": combine_dataset(
                getattr(left, "sample_stats_prior", None),
                getattr(right, "sample_stats_prior", None),
            ),
            "prior_predictive": combine_dataset(
                getattr(left, "prior_predictive", None),
                getattr(right, "prior_predictive", None),
            ),
            "observed_data": combine_dataset(
                getattr(left, "observed_data", None),
                getattr(right, "observed_data", None),
            ),
        }
    )
