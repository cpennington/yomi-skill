from functools import cached_property

import pandas
import pymc as pm
import pymc.math as pmmath
from scipy.special import expit, logit
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from skelo.model.elo import EloEstimator
import xarray
import numpy

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
                        ],
                        remainder="passthrough",
                    ),
                ),
                ("full", cls()),
            ],
            memory=memory,
            verbose=verbose,
        ).set_params(**params)

    def fit(self, X, y=None, sample_weight=None) -> "MUPCEloC":
        display(X)
        super().fit(X, y, sample_weight)
        return self

    @cached_property
    def model_(self):
        with pm.Model() as model:
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(len(self.mu_index_),))
            pc_elo_sum_intercept = pm.HalfNormal("pc_elo_sum_intercept", sigma=1.0)
            scaled_pc_elo_sum = pc_elo_sum_intercept
            pc_elo_estimate_logit = scaled_pc_elo_sum * logit(
                self.data_.pc_elo_estimate
            )

            elo_sum_intercept = pm.HalfNormal("elo_sum_intercept", sigma=1.0)
            scaled_elo_sum = elo_sum_intercept
            elo_estimate_logit = scaled_elo_sum * logit(self.data_.elo_estimate)

            mu_logit = (
                self.data_.non_mirror.to_numpy(int) * mu[self.data_.mup.to_numpy(int)]
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=mu_logit + pc_elo_estimate_logit + elo_estimate_logit,
                observed=self.y_,
            )
            if self.sample_weight_ is not None:
                pm.Potential(
                    "weighted",
                    pmmath.prod(pmmath.stack([self.sample_weight_, win_lik])),
                )
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        posterior = self.inf_data_["posterior"].mean(["chain", "draw"])

        non_mirror = (X.character_1 != X.character_2).astype(int)
        matchup_value = posterior.mu
        matchup = X.aggregate(
            lambda x: float(
                matchup_value.sel(matchup=f"{x.character_1}-{x.character_2}")
            ),
            axis=1,
        )

        scaled_pc_elo_sum = float(posterior.pc_elo_sum_intercept)
        pc_elo_estimate_logit = scaled_pc_elo_sum * logit(X.pc_elo_estimate)
        scaled_elo_sum = float(posterior.elo_sum_intercept)
        elo_estimate_logit = scaled_elo_sum * logit(X.elo_estimate)

        mu_logit = non_mirror * matchup

        prob_p1_win = expit(mu_logit + pc_elo_estimate_logit + elo_estimate_logit)

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
