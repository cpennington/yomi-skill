from ..model import YomiModel, elo_logit
import os
from scipy.special import expit
from IPython.core.display import display


class CharSkillEloSkillDeficit(YomiModel):
    model_filename = os.path.join(
        os.path.dirname(__file__), "char_skill_elo_skill_deficit.stan"
    )
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
            + (elo_logit_scale * elo_logit(games))
        )
