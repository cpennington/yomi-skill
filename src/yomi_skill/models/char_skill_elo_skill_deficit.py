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
        display(self.sample_dataframe.dtypes)
        mean_skill = self.player_char_skill.groupby(
            ["player", "character"]
        ).char_skill.agg(["mean", "std"])
        skill1 = games.apply(
            lambda x: mean_skill.loc[x.player_1, x.character_1], axis=1
        )
        skill2 = games.apply(
            lambda x: mean_skill.loc[x.player_2, x.character_2], axis=1
        )
        non_mirror = (games.character_1 != games.character_2).astype(int)
        matchup_value = self.matchups.groupby(["c1", "c2"]).win_rate.agg(
            ["mean", "std"]
        )
        matchup = games.apply(
            lambda x: matchup_value.loc[x.character_1, x.character_2], axis=1
        )
        elo_logit_scale = self.summary_dataframe.elo_logit_scale
        return expit(
            skill1["mean"]
            - skill2["mean"]
            + (non_mirror * matchup["mean"])
            + (elo_logit_scale["mean"] * elo_logit(games))
        )
