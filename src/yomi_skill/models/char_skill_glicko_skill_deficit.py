from ..model import elo_logit
from .pymc_model import PyMCModel
import os
from scipy.special import expit, logit
from IPython.core.display import display
from functools import cached_property
import pymc as pm


class CharSkillGlickoSkillDeficit(PyMCModel):
    model_name = "char_skill_glicko_skill_deficit"

    @cached_property
    def model(self):
        with pm.Model() as model:
            char_skill_deficit = pm.HalfNormal(
                "char_skill_deficit",
                sigma=1.0,
                shape=(self.constant_input["NC"], self.constant_input["NP"]),
            )
            char_skill = pm.Deterministic("char_skill", char_skill_deficit * -1)
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(self.constant_input["NM"]))
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)

            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                char_skill[
                    self.validation_input["char1T"] - 1,
                    self.validation_input["player1T"] - 1,
                ]
                - char_skill[
                    self.validation_input["char2T"] - 1,
                    self.validation_input["player2T"] - 1,
                ]
                + self.validation_input["non_mirrorT"]
                * mu[self.validation_input["mupT"] - 1]
                + elo_logit_scale * self.validation_input["skglicko_logitT"],
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.validation_input["winT"],
            )
        return model

    def predict(self, games):
        mean_skill = self.fit["posterior"].char_skill.mean(["chain", "draw"])
        skill1 = games.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_1, player=x.player_1)),
            axis=1,
        )
        skill2 = games.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_2, player=x.player_2)),
            axis=1,
        )
        non_mirror = (games.character_1 != games.character_2).astype(int)
        matchup_value = self.fit["posterior"].mu.mean(["chain", "draw"])
        matchup = games.aggregate(
            lambda x: float(
                matchup_value.sel(matchup=f"{x.character_1}-{x.character_2}")
            ),
            axis=1,
        )
        elo_logit_scale = float(
            self.fit["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        return expit(
            skill1
            - skill2
            + (non_mirror * matchup)
            + (elo_logit_scale * logit(games.glicko_estimate))
        )
