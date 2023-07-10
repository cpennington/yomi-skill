import hashlib
import io
import itertools
import logging
import os
import shutil
from functools import cached_property
from typing import List

import arviz
from cmdstanpy import CmdStanModel, from_csv

from ..model import YomiModel

logger = logging.getLogger(__name__)


class StanModel(YomiModel):
    model_filename: str
    required_input: List[str]

    @cached_property
    def model_name(self):
        model_name, _ = os.path.splitext(os.path.basename(self.model_filename))
        return model_name

    @cached_property
    def model_hash(self):
        with io.open(self.model_filename) as stan_code:
            model_hash = hashlib.md5()
            for chunk in stan_code:
                model_hash.update(chunk.encode("utf-8"))
            model_hash = model_hash.hexdigest()
        return model_hash

    @cached_property
    def fit(self) -> arviz.InferenceData:
        try:
            logger.info(f"Loading fit file from {self.netcdf_filename}")
            fit = arviz.InferenceData.from_netcdf(self.netcdf_filename)
            logger.info(f"Loaded {self.netcdf_filename}")
        except:
            logger.warning(f"Unable to load {self.netcdf_filename}")
            try:
                logger.info(f"Loading fit file from {self.fit_filename}")
                stan_fit = from_csv(self.fit_filename, "sample")
                logger.info(f"Loaded {self.fit_filename}")
            except:
                logger.info("Unable to load fit, resampling", exc_info=True)
                model = CmdStanModel(
                    stan_file=self.model_filename,
                )
                shutil.rmtree(self.data_dir, ignore_errors=True)
                os.makedirs(self.fit_filename, exist_ok=True)
                input_data = {
                    name: value
                    for name, value in itertools.chain(
                        self.constant_input.items(),
                        self.game_input.items(),
                        self.validation_input.items(),
                    )
                    if name in self.required_input
                }
                stan_fit = model.sample(
                    data=input_data,
                    iter_warmup=self.warmup,
                    iter_sampling=self.samples,
                    chains=4,
                    output_dir=self.fit_filename,
                )

                logger.info("Wrote fit to %s", self.fit_filename)
            fit = arviz.from_cmdstanpy(
                posterior=stan_fit,
                posterior_predictive="win_hat",
                observed_data={"win": self.game_input["win"]},
                log_likelihood="log_lik",
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
            )
            logger.info(f"Writing fit to {self.netcdf_filename}")
            fit.to_netcdf(self.netcdf_filename)
            logger.info(f"Wrote {self.netcdf_filename}")

        return fit
