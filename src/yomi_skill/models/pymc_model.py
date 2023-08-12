import hashlib
import inspect
import logging
from abc import abstractmethod
from functools import cached_property

import pymc as pm
import pymc.math as pmmath
import pymc.sampling_jax
from scipy.special import expit, logit

from ..model import YomiModel

logger = logging.getLogger(__name__)


class PyMCModel(YomiModel):
    model_: pm.Model

    @cached_property
    def model_hash(self):
        with open(inspect.getfile(self.__class__), "rb") as source:
            return hashlib.md5(source.read()).hexdigest()[:6]

    @cached_property
    def mu_m(self):
        return pm.Normal(
            "mu",
            0.0,
            sigma=0.5,
            shape=(len(self.data_.matchup__mup.dtype.categories),),
        )

    @cached_property
    def mu_logit_m(self):
        return (
            self.data_.matchup__non_mirror.to_numpy(int)
            * self.mu_m[self.data_.matchup__mup.cat.codes]
        )

    @cached_property
    def with_gem_m(self):
        return pm.Normal(
            "with_gem",
            0.0,
            sigma=0.5,
            shape=(len(self.data_.gem__with_gem_1.dtype.categories),),
        )

    @cached_property
    def against_gem_m(self):
        return pm.Normal(
            "against_gem",
            0.0,
            sigma=0.5,
            shape=(len(self.data_.gem__against_gem_1.dtype.categories),),
        )

    @cached_property
    def gem_effect_logit_m(self):
        return (
            self.with_gem_m[self.data_.gem__with_gem_1.cat.codes]
            + self.against_gem_m[self.data_.gem__against_gem_1.cat.codes]
            - self.with_gem_m[self.data_.gem__with_gem_2.cat.codes]
            - self.against_gem_m[self.data_.gem__against_gem_2.cat.codes]
        )

    @cached_property
    def global_pc_elo_estimate_logit_m(self):
        pc_elo_scale = pm.HalfNormal("pc_elo_scale", sigma=1.0)
        return pc_elo_scale * logit(self.data_.pc_elo__prob)

    @cached_property
    def global_elo_estimate_logit_m(self):
        elo_scale = pm.HalfNormal("elo_scale", sigma=1.0)
        return elo_scale * logit(self.data_.elo__prob)

    @cached_property
    def global_pc_glicko_estimate_logit_m(self):
        pc_glicko_scale = pm.HalfNormal("pc_glicko_scale", sigma=1.0)
        return pc_glicko_scale * logit(self.data_.pc_glicko__prob)

    @cached_property
    def global_glicko_estimate_logit_m(self):
        glicko_scale = pm.HalfNormal("glicko_scale", sigma=1.0)
        return glicko_scale * logit(self.data_.glicko__prob)

    @cached_property
    def pooled_pc_glicko_estimate_logit_m(self):
        pc_glicko_scale = pm.HalfNormal(
            "player_pc_glicko_scale", sigma=1.0, dims=("player",)
        )
        return (
            pc_glicko_scale[self.data_.min_games__player_1.cat.codes]
            * pc_glicko_scale[self.data_.min_games__player_2.cat.codes]
            * logit(self.data_.pc_glicko__prob)
        )

    @cached_property
    def pooled_glicko_estimate_logit_m(self):
        glicko_scale = pm.HalfNormal("player_glicko_scale", sigma=1.0, dims=("player",))
        return (
            glicko_scale[self.data_.min_games__player_1.cat.codes]
            * glicko_scale[self.data_.min_games__player_2.cat.codes]
            * logit(self.data_.glicko__prob)
        )

    def weighted_m(self, win_lik):
        if self.sample_weight_ is not None:
            pm.Potential(
                "weighted",
                pmmath.prod(pmmath.stack([self.sample_weight_, win_lik])),
            )

    def fit(self, X, y=None, sample_weight=None) -> "PyMCModel":
        super().fit(X, y, sample_weight)
        with self.model_:
            self.inf_data_ = pymc.sampling_jax.sample_blackjax_nuts(
                tune=self.warmup,
                draws=self.samples,
                chains=4,
                # postprocessing_chunks=1000,
                # var_names=["mu", "char_skill", "elo_logit_scale"],=True,
                idata_kwargs=dict(
                    # log_likelihood=True,
                    coords={
                        "matchup": X.matchup__mup.dtype.categories.values,
                        "with_gem_c": (
                            X.gem__with_gem_1.dtype.categories.values
                            if "gem__with_gem_1" in X.columns
                            else []
                        ),
                        "against_gem_c": (
                            X.gem__against_gem_1.dtype.categories.values
                            if "gem__against_gem_1" in X.columns
                            else []
                        ),
                        "player": X.min_games__player_1.dtype.categories.values,
                    },
                    dims={
                        "mu": ["matchup"],
                        "with_gem": ["with_gem_c"],
                        "against_gem": ["against_gem_c"],
                        "player_pc_glicko_scale": ["player"],
                        "player_glicko_scale": ["player"],
                    },
                ),
            )
        return self
