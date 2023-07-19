import logging
import inspect
import hashlib
import shutil
import os
from functools import cached_property
from abc import abstractmethod

import arviz
import jax
import pymc as pm
import pymc.sampling_jax

from ..model import YomiModel

logger = logging.getLogger(__name__)


class PyMCModel(YomiModel):
    model_: pm.Model

    @cached_property
    def model_hash(self):
        with open(inspect.getfile(self.__class__), "rb") as source:
            return hashlib.md5(source.read()).hexdigest()[:6]

    def fit(self, X, y=None, sample_weight=None) -> "PyMCModel":
        super().fit(X, y, sample_weight)
        with self.model_:
            self.inf_data_ = pymc.sampling_jax.sample_blackjax_nuts(
                tune=self.warmup,
                draws=self.samples,
                chains=4,
                postprocessing_chunks=1000,
                # var_names=["mu", "char_skill", "elo_logit_scale"],=True,
                idata_kwargs=dict(
                    # log_likelihood=True,
                    coords={
                        "matchup": X.matchup__mup.dtype.categories.values,
                    },
                    dims={
                        "mu": ["matchup"],
                    },
                ),
            )
        return self
