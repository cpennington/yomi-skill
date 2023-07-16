from functools import cached_property
import pandas
import pymc as pm
import pymc.math as pmmath
from scipy.special import expit, logit

from .pymc_model import PyMCModel


class Glicko(PyMCModel):
    model_name = "glicko"
    weight_key = "elo"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            glicko_logit_scale = pm.HalfNormal("glicko_logit_scale", sigma=1.0)
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=glicko_logit_scale * logit(self.data_.glicko_estimate),
                observed=self.y_,
            )
            if self.sample_weight_ is not None:
                pm.Potential(
                    "weighted",
                    pmmath.prod(pmmath.stack([self.sample_weight_, win_lik])),
                )
        return model

    def p1_win_chance(self, X: pandas.DataFrame):
        glicko_logit_scale = float(
            self.inf_data_["posterior"].glicko_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(glicko_logit_scale * logit(X.glicko_estimate))
        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
