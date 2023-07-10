#! /usr/bin/env python

import inspect
import logging

import arviz
import click
import click_log

from .model import YomiModel
from .models import *
from .render import *
from .yomi import historical_record

logger = logging.getLogger()
click_log.basic_config(logger)

MODELS = {
    model.model_name: model
    for model_type in YomiModel.__subclasses__()
    for model in model_type.__subclasses__()
}


@click.group()
@click_log.simple_verbosity_option(logger)
def cli():
    pass


@cli.command()
@click.option("--game", type=click.Choice(["yomi"]), default="yomi")
@click.option("--dest")
@click.option("--min-games", default=0, type=int)
@click.option("--with-versions/--no-versions", "versions", default=False)
@click.option("--new-data", "autodata", flag_value="new")
@click.option("--same-data", "autodata", flag_value="same")
@click.option("--static-root", default=".")
@click.option("--model", type=click.Choice(list(MODELS.keys())))
@click.option("--warmup", type=int)
@click.option("--samples", type=int)
def render(
    game, dest, min_games, versions, autodata, static_root, model, warmup, samples
):
    data_name = None
    hist_games = None
    if game == "yomi":
        data_name, hist_games = historical_record.games(autodata=autodata)

    if hist_games is None:
        raise Exception("No games loaded")

    fit_dir = f"fits/{data_name}"

    model = MODELS[model](
        hist_games,
        fit_dir,
        ["mu", "char_skill", "elo_logit_scale"],
        min_games,
        warmup=warmup,
        samples=samples,
        training_fraction=0.99999,
    )

    render = YomiRender(data_name, model)

    filename = render.render_matchup_comparator(game, dest, static_root=static_root)
    print(filename)


@cli.command()
@click.option("--game", type=click.Choice(["yomi"]), default="yomi")
@click.option("--min-games", default=0, type=int)
@click.option("--with-versions/--no-versions", "versions", default=False)
@click.option("--new-data", "autodata", flag_value="new")
@click.option("--same-data", "autodata", flag_value="same")
@click.option("--model", type=click.Choice(list(MODELS.keys())))
@click.option("--warmup", type=int)
@click.option("--samples", type=int)
def validate(game, min_games, versions, autodata, model, warmup, samples):
    data_name = None
    hist_games = None
    if game == "yomi":
        data_name, hist_games = historical_record.games(autodata=autodata)

    if hist_games is None:
        raise Exception("No games loaded")

    fit_dir = f"fits/{data_name}"

    model = MODELS[model](
        hist_games,
        fit_dir,
        ["mu", "char_skill", "elo_logit_scale", "brier_score"],
        min_games,
        warmup=warmup,
        samples=samples,
        training_fraction=0.8,
    )

    ess = arviz.ess(model.fit)
    display(ess.max())
    display(ess.min())
    display(model.posterior_brier_score)


if __name__ == "__main__":
    cli()
