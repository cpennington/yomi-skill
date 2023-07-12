from functools import cached_property
import pandas
import pymc as pm
from scipy.special import expit, logit

from ..model import elo_logit
from .pymc_model import PyMCModel


class PCGlickoOnly(PyMCModel):
    model_name = "pc_glicko_only"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            glicko_logit_scale = pm.HalfNormal("glicko_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                glicko_logit_scale * self.data_.skglicko_pc_logit,
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.y_,
            )
        return model

    def p1_win_chance(self, X: pandas.DataFrame):
        glicko_logit_scale = float(
            self.inf_data_["posterior"].glicko_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(glicko_logit_scale * logit(X.pc_glicko_estimate))
        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
