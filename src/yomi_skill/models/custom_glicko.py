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


class CustomGlicko(PyMCModel):
    model_name = "custom_glicko"
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
            ratings_delta = self.data_.glicko__r1 - self.data_.glicko__r2
            norm_deviation = self.data_.glicko__rd1**2 + self.data_.glicko__rd2**2
            deviation_scale = pm.HalfNormal("deviation_scale", sigma=1.0)
            g_deviation = ((deviation_scale * norm_deviation) + 1) ** (-0.5)
            rating_scale = pm.HalfNormal("rating_scale", sigma=1.0)

            pc_ratings_delta = self.data_.pc_glicko__r1 - self.data_.pc_glicko__r2
            pc_norm_deviation = (
                self.data_.pc_glicko__rd1**2 + self.data_.pc_glicko__rd2**2
            )
            pc_deviation_scale = pm.HalfNormal("pc_deviation_scale", sigma=1.0)
            pc_g_deviation = ((pc_deviation_scale * pc_norm_deviation) + 1) ** (-0.5)
            pc_rating_scale = pm.HalfNormal("pc_rating_scale", sigma=1.0)

            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.mu_logit_m
                + (rating_scale * g_deviation * ratings_delta)
                + (pc_rating_scale * pc_g_deviation * pc_ratings_delta),
                observed=self.y_,
            )
            self.weighted_m(win_lik)
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        posterior = self.inf_data_["posterior"].mean(["chain", "draw"])

        matchup_value = posterior.mu
        matchup = matchup_value.sel(matchup=X.matchup__mup.to_numpy())
        mu_logit = X.matchup__non_mirror * matchup

        ratings_delta = X.glicko__r1 - X.glicko__r2
        norm_deviation = X.glicko__rd1**2 + X.glicko__rd2**2
        deviation_scale = float(posterior.deviation_scale)
        g_deviation = ((deviation_scale * norm_deviation) + 1) ** (-0.5)
        rating_scale = float(posterior.rating_scale)

        prob_p1_win = expit(mu_logit + (rating_scale * g_deviation * ratings_delta))

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
