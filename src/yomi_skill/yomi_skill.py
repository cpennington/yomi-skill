#! /usr/bin/env python
import os
import multiprocessing

# Disable CUDA because only one gpu device allows only a single chain
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["XLA_FLAGS"] = "--xla_force_host_platform_device_count={}".format(
    multiprocessing.cpu_count()
)
import jax

print(jax.default_backend())
print(jax.devices())

import inspect
import logging

import arviz
import click
import click_log
from sklearn.model_selection import cross_validate

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
        fit_dir,
        min_games,
        warmup=warmup,
        samples=samples,
    )

    # model.fit(hist_games, hist_games.win)
    # ess = arviz.ess(model.inf_data_)
    # display(ess.max())
    # display(ess.min())
    scores = cross_validate(
        model,
        hist_games,
        y=hist_games.win,
        cv=5,
        scoring=(
            "neg_brier_score",
            "neg_log_loss",
            "roc_auc",
            "precision",
            "recall",
            "f1",
        ),
    )
    display(pandas.DataFrame(scores).describe())


if __name__ == "__main__":
    cli()
