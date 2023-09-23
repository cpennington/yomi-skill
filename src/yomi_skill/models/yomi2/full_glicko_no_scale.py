from functools import cached_property

import pandas
import pymc as pm
from scipy.special import expit, logit
from skelo.model.glicko2 import Glicko2Estimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ...model import (
    matchup_transformer,
    min_games_transformer,
    render_transformer,
    gem_effect_transformer,
)
from ..pymc_model import PyMCModel


class Y2FullGlickoNoScale(PyMCModel):
    model_name = "y2_full_glicko_no_scale"
    weight_key = "pc_glicko"

    @classmethod
    def pipeline(cls, memory=None, verbose=False, prefit_games=None, **params):
        glicko = Glicko2Estimator(
            key1_field="player_1",
            key2_field="player_2",
            timestamp_field="match_date",
            **{
                name.replace("transform__glicko__", ""): value
                for name, value in params.items()
                if name.startswith("transform__glicko__")
            },
        )
        glicko.fit(prefit_games, prefit_games.win)

        pc_glicko = Glicko2Estimator(
            key1_field="player_character_1",
            key2_field="player_character_2",
            timestamp_field="match_date",
            **{
                name.replace("transform__pc_glicko__", ""): value
                for name, value in params.items()
                if name.startswith("transform__pc_glicko__")
            },
        )
        pc_glicko.fit(prefit_games, prefit_games.win)
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
                                    initial_ratings=glicko.rating_model.ratings,
                                ),
                                ["player_1", "player_2", "match_date"],
                            ),
                            (
                                "pc_glicko",
                                Glicko2Estimator(
                                    key1_field="player_character_1",
                                    key2_field="player_character_2",
                                    timestamp_field="match_date",
                                    initial_ratings=pc_glicko.rating_model.ratings,
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
                                "gem",
                                gem_effect_transformer,
                                ["character_1", "gem_1", "character_2", "gem_2"],
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
                "with_gem": self.data_.gem__with_gem_1.dtype.categories.values,
                "against_gem": self.data_.gem__against_gem_1.dtype.categories.values,
                "player": self.data_.min_games__player_1.dtype.categories.values,
            }
        ) as model:
            player_global_scale = pm.Uniform("player_global_scale", upper=1, lower=0)
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.mu_logit_m
                + self.gem_effect_logit_m
                + (player_global_scale * logit(self.data_.pc_glicko__prob))
                + ((1 - player_global_scale) * logit(self.data_.glicko__prob)),
                observed=self.y_,
            )
            self.weighted_m(win_lik)
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        posterior = self.inf_data_["posterior"].mean(["chain", "draw"])

        matchup = posterior.mu.sel(matchup=X.matchup__mup.to_numpy())

        with_gem_1 = posterior.with_gem.sel(with_gem_c=X.gem__with_gem_1.to_numpy())
        with_gem_2 = posterior.with_gem.sel(with_gem_c=X.gem__with_gem_2.to_numpy())
        against_gem_1 = posterior.against_gem.sel(
            against_gem_c=X.gem__against_gem_1.to_numpy()
        )
        against_gem_2 = posterior.against_gem.sel(
            against_gem_c=X.gem__against_gem_2.to_numpy()
        )

        global_pc_glicko_estimate_logit = logit(X.pc_glicko__prob)
        global_glicko_estimate_logit = logit(X.glicko__prob)

        mu_logit = X.matchup__non_mirror * matchup

        prob_p1_win = expit(
            mu_logit
            + with_gem_1
            + against_gem_1
            - with_gem_2
            - against_gem_2
            + global_pc_glicko_estimate_logit * float(posterior.player_global_scale)
            + global_glicko_estimate_logit * (1 - float(posterior.player_global_scale))
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
