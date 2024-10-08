from functools import cached_property

import numpy
import pandas
import pymc as pm
import pymc.math as pmmath
import xarray
from scipy.special import expit, logit
from skelo.model.elo import EloEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ..model import matchup_transformer, min_games_transformer, render_transformer
from .pymc_model import PyMCModel


class Full(PyMCModel):
    model_name = "full"
    weight_key = "pc_elo"

    @classmethod
    def pipeline(cls, memory=None, verbose=False, **params):
        return Pipeline(
            [
                (
                    "transform",
                    ColumnTransformer(
                        [
                            (
                                "elo",
                                EloEstimator(
                                    key1_field="player_1",
                                    key2_field="player_2",
                                    timestamp_field="match_date",
                                ),
                                ["player_1", "player_2", "match_date"],
                            ),
                            (
                                "pc_elo",
                                EloEstimator(
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
        with pm.Model() as model:
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.mu_logit_m
                + self.global_pc_elo_estimate_logit_m
                + self.global_elo_estimate_logit_m,
                observed=self.y_,
            )
            self.weighted_m(win_lik)
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        posterior = self.inf_data_["posterior"].mean(["chain", "draw"])

        matchup_value = posterior.mu
        matchup = X.aggregate(
            lambda x: float(matchup_value.sel(matchup=x.matchup__mup)),
            axis=1,
        )

        pc_elo_estimate_logit = float(posterior.pc_elo_scale) * logit(X.pc_elo__prob)
        elo_estimate_logit = float(posterior.elo_scale) * logit(X.elo__prob)

        mu_logit = X.matchup__non_mirror * matchup

        prob_p1_win = expit(mu_logit + pc_elo_estimate_logit + elo_estimate_logit)

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
