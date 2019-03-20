#! /usr/bin/env python

import pandas
import yomi.historical_record
import bacon
from render import *
import click


@click.command()
@click.option("--game", type=click.Choice(["yomi", "bacon"]), default="yomi")
@click.option("--dest")
def render(game, dest):
    if game == "yomi":
        data_name, hist_games = yomi.historical_record.games()
    elif game == "bacon":
        data_name, hist_games = bacon.games()

    fit_dir = f"fits/{data_name}"
    from model import YomiModel

    model = YomiModel(
        hist_games,
        fit_dir,
        "char_skill_elo_skill_deficit.stan",
        ["mu", "char_skill", "elo_logit_scale", "log_lik", "win_hat"],
    )

    render = YomiRender(data_name, model, 1500, 2000)

    filename = render.render_matchup_comparator(game, dest)
    print(filename)


if __name__ == "__main__":
    render()
