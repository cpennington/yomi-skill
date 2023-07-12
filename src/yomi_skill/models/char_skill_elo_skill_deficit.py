import os

import pandas
from scipy.special import expit

from ..model import elo_logit
from .stan_model import StanModel


class CharSkillEloSkillDeficit(StanModel):
    model_filename = os.path.join(
        os.path.dirname(__file__), "char_skill_elo_skill_deficit.stan"
    )
    model_name = "char_skill_elo_skill_deficit"

    required_input = [
        "NTG",
        "NVG",
        "NM",
        "NP",
        "NC",
        "winT",
        "mupT",
        "non_mirrorT",
        "char1T",
        "char2T",
        "player1T",
        "player2T",
        "elo_logitT",
        "winV",
        "mupV",
        "non_mirrorV",
        "char1V",
        "char2V",
        "player1V",
        "player2V",
        "elo_logitV",
    ]

    def p1_win_chance(self, X: pandas.DataFrame) -> pandas.DataFrame:
        mean_skill = self.inf_data_["posterior"].char_skill.mean(["chain", "draw"])
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
