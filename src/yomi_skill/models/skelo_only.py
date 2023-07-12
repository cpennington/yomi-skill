from functools import cached_property
import pandas
import pymc as pm
from scipy.special import expit, logit

from ..model import elo_logit
from .pymc_model import PyMCModel


class SkeloOnly(PyMCModel):
    model_name = "skelo_only"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                elo_logit_scale * self.data_.skelo_logit,
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.y_,
            )
        return model

    def p1_win_chance(self, X: pandas.DataFrame):
        elo_logit_scale = float(
            self.inf_data_["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(elo_logit_scale * logit(X.elo_estimate))
        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
