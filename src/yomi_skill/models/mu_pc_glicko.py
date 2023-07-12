from functools import cached_property

import pandas
import pymc as pm
from scipy.special import expit, logit
import xarray
import numpy

from .pymc_model import PyMCModel


class MUPCGlicko(PyMCModel):
    model_name = "mu_pc_glicko"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(len(self.mu_index_),))
            glicko_logit_scale = pm.HalfNormal("glicko_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                self.data_.non_mirror.to_numpy(int) * mu[self.data_.mup.to_numpy(int)]
                + glicko_logit_scale * self.data_.skglicko_pc_logit,
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.y_,
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
        glicko_logit_scale = float(
            self.inf_data_["posterior"].glicko_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(
            (non_mirror * matchup) + (glicko_logit_scale * logit(X.pc_glicko_estimate))
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
