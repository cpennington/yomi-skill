#! /usr/bin/env python

from .yomi import historical_record
from .render import *
from .model import YomiModel
import click
import click_log
import logging

logger = logging.getLogger()
click_log.basic_config(logger)

@click.group()
@click_log.simple_verbosity_option(logger)
def cli():
    pass

@cli.command()
@click.option("--game", type=click.Choice(["yomi"]), default="yomi")
@click.option("--dest")
@click.option("--min-games", default=50, type=int)
@click.option("--with-versions/--no-versions", "versions", default=False)
@click.option("--new-data", "autodata", flag_value="new")
@click.option("--same-data", "autodata", flag_value="same")
@click.option("--static-root", default=".")
def render(game, dest, min_games, versions, autodata, static_root):
    if game == "yomi":
        data_name, hist_games = historical_record.games(autodata=autodata)

    fit_dir = f"fits/{data_name}"

    display(hist_games)

    if versions:
        model = YomiModel(
            hist_games,
            fit_dir,
            "char_skill_elo_skill_deficit_versioned_hier.stan",
            [
                "mu_mean",
                "mu_std",
                "vmu",
                "char_skill",
                "elo_logit_scale",
                # "log_lik",
                # "win_hat",
            ],
            min_games,
        )
    else:
        model = YomiModel(
            hist_games,
            fit_dir,
            "char_skill_elo_skill_deficit.stan",
            ["mu", "char_skill", "elo_logit_scale"
            #  , "log_lik", "win_hat"
             ],
            min_games,
        )

    render = YomiRender(data_name, model, 1500, 2000)

    filename = render.render_matchup_comparator(game, dest, static_root=static_root)
    print(filename)


if __name__ == "__main__":
    cli()
