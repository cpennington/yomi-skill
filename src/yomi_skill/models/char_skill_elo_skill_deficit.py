from ..model import YomiModel
import os


class CharSkillEloSkillDeficit(YomiModel):
    model_filename = os.path.join(
        os.path.dirname(__file__), "char_skill_elo_skill_deficit.stan"
    )
