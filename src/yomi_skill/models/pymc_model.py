import logging
import inspect
import hashlib
import shutil
import os
from functools import cached_property

import arviz
import pymc as pm
import pymc.sampling_jax

from ..model import YomiModel

logger = logging.getLogger(__name__)


class PyMCModel(YomiModel):
    model: pm.Model

    @cached_property
    def model_hash(self):
        with open(inspect.getfile(self.__class__), "rb") as source:
            return hashlib.md5(source.read()).hexdigest()[:6]

    @cached_property
    def fit(self) -> arviz.InferenceData:
        try:
            logger.info(f"Loading fit file from {self.netcdf_filename}")
            fit = arviz.InferenceData.from_netcdf(self.netcdf_filename)
            logger.info(f"Loaded {self.netcdf_filename}")
            return fit
        except:
            logger.warning(f"Unable to load {self.netcdf_filename}, re-sampling")
            shutil.rmtree(self.data_dir, ignore_errors=True)
            with self.model:
                fit = pymc.sampling_jax.sample_blackjax_nuts(
                    tune=self.warmup,
                    draws=self.samples,
                    chains=4,
                    # var_names=["mu", "char_skill", "elo_logit_scale"],
                    idata_kwargs=dict(
                        coords={
                            "character": self.characters,
                            "player": self.players,
                            "matchup": [
                                f"{c1}-{c2}"
                                for ((c1, c2), _) in sorted(
                                    self.mu_index.items(), key=lambda x: x[1]
                                )
                            ],
                        },
                        dims={
                            "char_skill": ["character", "player"],
                            "mu": ["matchup"],
                        },
                    ),
                )
                logger.info(f"Writing fit to {self.netcdf_filename}")
                os.makedirs(os.path.dirname(self.netcdf_filename), exist_ok=True)
                fit.to_netcdf(self.netcdf_filename)
                logger.info(f"Wrote {self.netcdf_filename}")

                return fit
        raise Exception("Failed to return fit")
