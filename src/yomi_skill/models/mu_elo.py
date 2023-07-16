from functools import cached_property

import pandas
import pymc as pm
import pymc.math as pmmath
from scipy.special import expit, logit
import xarray
import numpy

from .pymc_model import PyMCModel


class MUElo(PyMCModel):
    model_name = "mu_elo"
    weight_key = "elo"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(len(self.mu_index_),))
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=self.data_.non_mirror.to_numpy(int)
                * mu[self.data_.mup.to_numpy(int)]
                + elo_logit_scale * logit(self.data_.elo_estimate),
                observed=self.y_,
            )
            if self.sample_weight_ is not None:
                pm.Potential(
                    "weighted",
                    pmmath.prod(pmmath.stack([self.sample_weight_, win_lik])),
                )
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        non_mirror = (X.character_1 != X.character_2).astype(int)
        matchup_value = self.inf_data_["posterior"].mu.mean(["chain", "draw"])
        matchup = X.aggregate(
            lambda x: float(
                matchup_value.sel(matchup=f"{x.character_1}-{x.character_2}")
            ),
            axis=1,
        )
        elo_logit_scale = float(
            self.inf_data_["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(
            (non_mirror * matchup) + (elo_logit_scale * logit(X.elo_estimate))
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
