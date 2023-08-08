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
import tempfile

import arviz
import click
import click_log
from sklearn.model_selection import cross_validate

from .model import YomiModel, weight_by
from .models import *
from .render import *
from .yomi import historical_record

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()
click_log.basic_config(logger)

from sklearn import set_config

set_config(transform_output="pandas")

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
@click.option("--min-games", default=0, type=int)
@click.option("--dest")
@click.option(
    "--model", type=click.Choice(list(MODELS.keys())), default="full_glicko_no_scale"
)
@click.option("--warmup", type=int)
@click.option("--samples", type=int)
def render(dest, min_games, model, warmup, samples):
    tournament_games = historical_record.latest_tournament_games()
    sirlin_games = historical_record.sirlin_db()
    games = pandas.concat([tournament_games, sirlin_games]).reset_index(drop=True)
    hist_games = historical_record.augment_dataset(games)

    pipeline = (
        MODELS[model]
        .pipeline(
            transform__glicko__initial_time=hist_games.match_date.min(),
            transform__pc_glicko__initial_time=hist_games.match_date.min(),
            model__min_games=min_games,
            model__warmup=warmup,
            model__samples=samples,
            # transform__elo__default_k=16,
            # transform__pc_elo__default_k=1,
            transform__glicko__initial_value=(1500.0, 50, 0.059),
            transform__pc_glicko__initial_value=(1500.0, 40, 0.027),
            transform__glicko__rating_period="1D",
            transform__pc_glicko__rating_period="8D",
            # transform__elo__rating_factor=1135.77,  # 200-point rating difference corresponds to 60% win chance
        )
        .fit(hist_games, hist_games.win)
    )

    render = YomiRender(pipeline)

    render.render_matchup_comparator(dest)


@cli.command()
@click.option("--min-games", default=0, type=int)
@click.option("--model", type=click.Choice(list(MODELS.keys())), default="full")
@click.option("--warmup", type=int)
@click.option("--samples", type=int)
def validate(min_games, model, warmup, samples):
    tournament_games = historical_record.latest_tournament_games()
    sirlin_games = historical_record.sirlin_db()
    games = pandas.concat([tournament_games, sirlin_games]).reset_index(drop=True)
    hist_games = historical_record.augment_dataset(games)

    model = MODELS[model](
        tempfile.mkdtemp(),
        min_games,
        warmup=warmup,
        samples=samples,
    )
    hist_games = weight_by(hist_games, model.weight_key)
    display(hist_games.sort_values("weight"))

    model.fit(hist_games, hist_games.win)
    display(arviz.summary(model.inf_data_))

    display(
        pandas.concat(
            [
                hist_games,
                pandas.DataFrame(model.predict_proba(hist_games)),
            ]
        )
    )

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
        fit_params=dict(
            sample_weight=hist_games.weight,
        ),
    )
    display(pandas.DataFrame(scores).describe())


if __name__ == "__main__":
    cli()
