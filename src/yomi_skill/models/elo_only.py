from ..model import elo_logit
from .pymc_model import PyMCModel
import os
from scipy.special import expit
from IPython.core.display import display
from functools import cached_property
import pymc as pm


class EloOnly(PyMCModel):
    model_name = "elo_only"

    @cached_property
    def model(self):
        with pm.Model() as model:
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                elo_logit_scale * self.validation_input["elo_logitT"],
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.validation_input["winT"],
            )
        return model

    def predict(self, games):
        elo_logit_scale = float(
            self.fit["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        return expit(elo_logit_scale * elo_logit(games))
