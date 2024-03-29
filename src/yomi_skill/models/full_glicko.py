from functools import cached_property

import numpy
import pandas
import pymc as pm
import pymc.math as pmmath
import xarray
from scipy.special import expit, logit
from skelo.model.glicko2 import Glicko2Estimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ..model import matchup_transformer, min_games_transformer, render_transformer
from .pymc_model import PyMCModel


class FullGlicko(PyMCModel):
    model_name = "full_glicko"
    weight_key = "pc_glicko"

    @classmethod
    def pipeline(cls, memory=None, verbose=False, **params):
        return Pipeline(
            [
                (
                    "transform",
                    ColumnTransformer(
                        [
                            (
                                "glicko",
                                Glicko2Estimator(
                                    key1_field="player_1",
                                    key2_field="player_2",
                                    timestamp_field="match_date",
                                ),
                                ["player_1", "player_2", "match_date"],
                            ),
                            (
                                "pc_glicko",
                                Glicko2Estimator(
                                    key1_field="player_character_1",
                                    key2_field="player_character_2",
                                    timestamp_field="match_date",
                                ),
                                [
                                    "player_character_1",
                                    "player_character_2",
                                    "match_date",
                                ],
                            ),
                            (
                                "min_games",
                                min_games_transformer,
                                ["player_1", "player_2"],
                            ),
                            (
                                "matchup",
                                matchup_transformer,
                                ["character_1", "character_2"],
                            ),
                            (
                                "render",
                                render_transformer,
                                ["match_date", "win", "public"],
                            ),
                        ],
                        remainder="drop",
                    ),
                ),
                ("model", cls()),
            ],
            memory=memory,
            verbose=verbose,
        ).set_params(**params)

    @cached_property
    def model_(self):
        with pm.Model(
            coords={
                "matchup": self.data_.matchup__mup.dtype.categories.values,
                "player": self.data_.min_games__player_1.dtype.categories.values,
            }
        ) as model:
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.mu_logit_m
                + self.global_pc_glicko_estimate_logit_m
                + self.global_glicko_estimate_logit_m,
                # + self.pooled_pc_glicko_estimate_logit_m
                # + self.pooled_glicko_estimate_logit_m,
                observed=self.y_,
            )
            self.weighted_m(win_lik)
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        posterior = self.inf_data_["posterior"].mean(["chain", "draw"])

        matchup_value = posterior.mu
        matchup = matchup_value.sel(matchup=X.matchup__mup.to_numpy())

        global_pc_glicko_estimate_logit = float(posterior.pc_glicko_scale) * logit(
            X.pc_glicko__prob
        )
        global_glicko_estimate_logit = float(posterior.glicko_scale) * logit(
            X.glicko__prob
        )
        # player_pc_glicko_estimate_logit = (
        #     posterior.player_pc_glicko_scale.reindex(
        #         fill_value=0, player=X.min_games__player_1.dtype.categories.values
        #     )
        #     .sel(player=X.min_games__player_1.to_numpy())
        #     .to_numpy()
        #     * posterior.player_pc_glicko_scale.reindex(
        #         fill_value=0, player=X.min_games__player_2.dtype.categories.values
        #     )
        #     .sel(player=X.min_games__player_2.to_numpy())
        #     .to_numpy()
        #     * logit(X.pc_glicko__prob)
        # )
        # player_glicko_estimate_logit = (
        #     posterior.player_glicko_scale.reindex(
        #         fill_value=0, player=X.min_games__player_1.dtype.categories.values
        #     )
        #     .sel(player=X.min_games__player_1.to_numpy())
        #     .to_numpy()
        #     * posterior.player_glicko_scale.reindex(
        #         fill_value=0, player=X.min_games__player_2.dtype.categories.values
        #     )
        #     .sel(player=X.min_games__player_2.to_numpy())
        #     .to_numpy()
        #     * logit(X.glicko__prob)
        # )

        mu_logit = X.matchup__non_mirror * matchup

        prob_p1_win = expit(
            mu_logit
            + global_pc_glicko_estimate_logit
            + global_glicko_estimate_logit
            # + player_glicko_estimate_logit
            # + player_pc_glicko_estimate_logit
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
