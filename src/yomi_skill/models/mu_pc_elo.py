from functools import cached_property

import pandas
import pymc as pm
import pymc.math as pmmath
from scipy.special import expit, logit
from skelo.model.elo import EloEstimator
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import xarray
import numpy

from ..model import matchup_transformer, min_games_transformer
from .pymc_model import PyMCModel


class MUPCElo(PyMCModel):
    model_name = "mu_pc_elo"
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
            mu = pm.Normal(
                "mu",
                0.0,
                sigma=0.5,
                shape=(len(self.data_.matchup__mup.dtype.categories),),
            )
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.data_.matchup__non_mirror.to_numpy(int)
                * mu[self.data_.matchup__mup]
                + elo_logit_scale * logit(self.data_.pc_elo__prob),
                observed=self.y_,
            )
            if self.sample_weight_ is not None:
                pm.Potential(
                    "weighted",
                    pmmath.prod(pmmath.stack([self.sample_weight_, win_lik])),
                )
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        matchup_value = self.inf_data_["posterior"].mu.mean(["chain", "draw"])
        matchup = X.aggregate(
            lambda x: float(matchup_value.sel(matchup=x.matchup__mup)),
            axis=1,
        )
        elo_logit_scale = float(
            self.inf_data_["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(
            (X.matchup__non_mirror * matchup)
            + (elo_logit_scale * logit(X.pc_elo__prob))
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
