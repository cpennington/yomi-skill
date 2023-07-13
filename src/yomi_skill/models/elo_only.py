from functools import cached_property
import pandas
import pymc as pm
import pymc.math as pmmath
from scipy.special import expit

from ..model import elo_logit
from .pymc_model import PyMCModel


class EloOnly(PyMCModel):
    model_name = "elo_only"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                elo_logit_scale * self.data_.elo_logit,
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.y_,
            )
            pm.Potential(
                "weighted", pmmath.prod(pmmath.stack([self.sample_weights_, win_lik]))
            )
        return model

    def p1_win_chance(self, X: pandas.DataFrame):
        elo_logit_scale = float(
            self.inf_data_["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(elo_logit_scale * elo_logit(X))
        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
