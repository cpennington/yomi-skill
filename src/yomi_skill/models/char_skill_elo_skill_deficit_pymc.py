from functools import cached_property

import pandas
import pymc as pm
from scipy.special import expit

from ..model import elo_logit
from .pymc_model import PyMCModel


class CharSkillEloSkillDeficitPyMC(PyMCModel):
    model_name = "char_skill_elo_skill_deficit_pymc"

    @cached_property
    def model_(self):
        with pm.Model() as model:
            char_skill_deficit = pm.HalfNormal(
                "char_skill_deficit",
                sigma=1.0,
                shape=(len(self.character_index_), len(self.player_index_)),
            )
            char_skill = pm.Deterministic("char_skill", char_skill_deficit * -1)
            mu = pm.Normal("mu", 0.0, sigma=0.5, shape=(len(self.mu_index_),))
            elo_logit_scale = pm.HalfNormal("elo_logit_scale", sigma=1.0)
            print(self.data_.character_ix_1.dtype)
            print(self.data_.player_ix_1.dtype)
            win_chance_logit = pm.Deterministic(
                "win_chance_logit",
                char_skill[
                    self.data_.character_ix_1,
                    self.data_.player_ix_1,
                ]
                - char_skill[
                    self.data_.character_ix_2,
                    self.data_.player_ix_2,
                ]
                + self.data_.non_mirror.to_numpy(int) * mu[self.data_.mup.to_numpy(int)]
                + elo_logit_scale * self.data_.elo_logit,
            )
            win_lik = pm.Bernoulli(
                "win_lik",
                logit_p=win_chance_logit,
                observed=self.y_,
            )
        return model

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        mean_skill = self.fill_untrained_players(
            self.inf_data_["posterior"].char_skill.mean(["chain", "draw"]), X
        )
        skill1 = X.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_1, player=x.player_1)),
            axis=1,
        )
        skill2 = X.aggregate(
            lambda x: float(mean_skill.sel(character=x.character_2, player=x.player_2)),
            axis=1,
        )
        non_mirror = (X.character_1 != X.character_2).astype(int)
        matchup_value = self.inf_data_["posterior"].mu.mean(["chain", "draw"])
        matchup = X.aggregate(
            lambda x: float(
                matchup_value.sel(matchup=f"{x.character_1}-{x.character_2}")
            ),
            axis=1,
        )
        elo_logit_scale = float(
            self.inf_data_["posterior"].elo_logit_scale.mean(["chain", "draw"])
        )
        prob_p1_win = expit(
            skill1 - skill2 + (non_mirror * matchup) + (elo_logit_scale * elo_logit(X))
        )

        return pandas.DataFrame(
            {1: prob_p1_win, 0: 1 - prob_p1_win}, columns=self.classes_
        )
