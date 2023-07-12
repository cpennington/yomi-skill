import hashlib
import io
import itertools
import logging
import os
import shutil
from functools import cached_property
from typing import Any, Dict, List

import arviz
from cmdstanpy import CmdStanModel, from_csv
from scipy.special import logit

from ..model import YomiModel, elo_logit

logger = logging.getLogger(__name__)


class StanModel(YomiModel):
    model_filename: str
    model_name: str
    required_input: List[str]

    @cached_property
    def constant_input(self) -> Dict[str, Any]:
        return {
            # "NPT": len(self.player_tournament_index),
            "NG": len(self.data_),
            "NM": len(self.mu_index_),
            "NP": len(self.player_index_),
            "NC": len(self.characters_),
            "NMV": len(self.version_mu_index_),
            "mu_for_v": [
                self.mu_index_[(c1, c2)]
                for ((c1, v1, c2, v2), vix) in sorted(
                    self.version_mu_index_.items(), key=lambda i: i[1]
                )
            ],
            # Disable predictions
            "predict": 0,
        }

    @cached_property
    def game_input(self) -> Dict[str, Any]:
        elo_sum = self.data_.elo_before_1 + self.data_.elo_before_2
        scaled_weights = 0.25 + 1.75 * (elo_sum - elo_sum.min()) / (
            elo_sum.max() - elo_sum.min()
        )
        normalized_weights = scaled_weights / scaled_weights.sum() * len(self.data_)

        return {
            "games": self.data_,
            # "tp": tournament_player,
            "win": self.y_.to_numpy(int),
            # "pt1": self.data_.apply(
            #     lambda r: self.player_tournament_index[(r.player_1, r.tournament_name)],
            #     axis=1,
            # ),
            # "pt2": self.data_.apply(
            #     lambda r: self.player_tournament_index[(r.player_2, r.tournament_name)],
            #     axis=1,
            # ),
            "mup": self.data_.mup.to_numpy(int) + 1,
            "vmup": self.data_.vmup.to_numpy(int) + 1,
            "non_mirror": self.data_.non_mirror.to_numpy(int),
            # "prev_tournament": self.player_tournament_dates.previous.to_numpy(int).apply(
            #     lambda x: x + 1
            # ),
            "char1": self.data_.character_ix_1.to_numpy(int) + 1,
            "char2": self.data_.character_ix_2.to_numpy(int) + 1,
            "version1": self.data_.version_ix_1.to_numpy(int) + 1,
            "version2": self.data_.version_ix_2.to_numpy(int) + 1,
            "player1": self.data_.player_ix_1.to_numpy(int) + 1,
            "player2": self.data_.player_ix_2.to_numpy(int) + 1,
            "elo_logit": self.data_.elo_logit.to_numpy(),
            "skelo_logit": self.data_.skelo_logit.to_numpy(),
            "skglicko_logit": self.data_.skglicko_logit.to_numpy(),
            # Scale so that mininum elo sum gets 0.25 weight, max sum gets 2 weight
            "obs_weights": normalized_weights.to_numpy(),
        }

    @cached_property
    def model_hash(self):
        with io.open(self.model_filename) as stan_code:
            model_hash = hashlib.md5()
            for chunk in stan_code:
                model_hash.update(chunk.encode("utf-8"))
            model_hash = model_hash.hexdigest()
        return model_hash

    def fit(self, X, y=None) -> "StanModel":
        super().fit(X, y)
        netcdf_file = self.netcdf_filename_()
        fit_file = self.fit_filename_()
        try:
            logger.info(f"Loading fit file from {netcdf_file}")
            self.inf_data_ = arviz.InferenceData.from_netcdf(netcdf_file)
            logger.info(f"Loaded {netcdf_file}")
        except:
            logger.warning(f"Unable to load {netcdf_file}")
            try:
                logger.info(f"Loading fit file from {fit_file}")
                stan_fit = from_csv(fit_file, "sample")
                logger.info(f"Loaded {fit_file}")
            except:
                logger.info("Unable to load fit, resampling", exc_info=True)
                model = CmdStanModel(
                    stan_file=self.model_filename,
                )
                shutil.rmtree(self.data_dir, ignore_errors=True)
                os.makedirs(fit_file, exist_ok=True)
                input_data = {
                    name: value
                    for name, value in itertools.chain(
                        self.constant_input.items(),
                        self.game_input.items(),
                    )
                    if name in self.required_input
                }
                stan_fit = model.sample(
                    data=input_data,
                    iter_warmup=self.warmup,
                    iter_sampling=self.samples,
                    chains=4,
                    output_dir=fit_file,
                )

                logger.info("Wrote fit to %s", fit_file)
            self.inf_data_ = arviz.from_cmdstanpy(
                posterior=stan_fit,
                posterior_predictive="win_hat",
                observed_data={"win": self.game_input["win"]},
                log_likelihood="log_lik",
                coords={
                    "character": self.characters_,
                    "player": self.players_,
                    "matchup": [
                        f"{c1}-{c2}"
                        for ((c1, c2), _) in sorted(
                            self.mu_index_.items(), key=lambda x: x[1]
                        )
                    ],
                },
                dims={
                    "char_skill": ["character", "player"],
                    "mu": ["matchup"],
                },
            )
            logger.info(f"Writing fit to {netcdf_file}")
            self.inf_data_.to_netcdf(netcdf_file)
            logger.info(f"Wrote {netcdf_file}")

        return self
