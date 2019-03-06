#! /usr/bin/env python

from character import Character, character_category
import pandas
from historical_record import games
from render import *

if __name__ == "__main__":
    data_name, hist_games = games()
    fit_dir = f"fits/{data_name}"
    from model import YomiModel

    model = YomiModel(
        hist_games,
        fit_dir,
        "char_skill_elo_skill_deficit.stan",
        ["mu", "char_skill", "elo_logit_scale", "log_lik", "win_hat"],
    )

    render = YomiRender(data_name, model, 1500, 2000)

    filename = render.render_matchup_comparator()
    print(filename)
