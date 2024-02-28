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

import logging

import click
import click_log
from sklearn.model_selection import cross_validate

from .model import YomiModel, weight_by
from .models import *
from .models.yomi2 import *
from .render import *
from .games import yomi, yomi2 as games_yomi2

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()
click_log.basic_config(logger)

from sklearn import set_config

set_config(transform_output="pandas")

from .models.pymc_model import PyMCModel

MODELS = {
    model.model_name: model
    for model_type in YomiModel.__subclasses__()
    for model in model_type.__subclasses__()
}


@click.group()
@click_log.simple_verbosity_option(logger)
def cli():
    pass


@cli.group()
def yomi1():
    pass


@cli.group()
def yomi2():
    pass


@yomi1.command()
@click.option("--min-games", default=0, type=int)
@click.option(
    "--model", type=click.Choice(list(MODELS.keys())), default="full_glicko_no_scale"
)
@click.option("--warmup", type=int, default=500)
@click.option("--samples", type=int, default=1000)
def render(min_games, model, warmup, samples):
    tournament_games = yomi.latest_tournament_games()
    sirlin_games = yomi.sirlin_db()
    games = pandas.concat([tournament_games, sirlin_games]).reset_index(drop=True)
    hist_games = yomi.augment_dataset(games)

    pipeline = (
        MODELS[model]
        .pipeline(
            rating_periods__player__kw_args=dict(field_prefix="player", threshold=1),
            rating_periods__player_character__kw_args=dict(
                field_prefix="player_character", threshold=3
            ),
            transform__glicko__initial_time=hist_games.match_date.min(),
            transform__pc_glicko__initial_time=hist_games.match_date.min(),
            model__min_games=min_games,
            model__warmup=warmup,
            model__samples=samples,
            # transform__elo__default_k=16,
            # transform__pc_elo__default_k=1,
            transform__glicko__initial_value=(1500.0, 50, 0.059),
            transform__pc_glicko__initial_value=(1500.0, 40, 0.027),
            # transform__elo__rating_factor=1135.77,  # 200-point rating difference corresponds to 60% win chance
        )
        .fit(hist_games, hist_games.win)
    )

    render = YomiRender(pipeline, "src-js/data/yomi")
    render.render_aggregate_skill()
    render.render_players()
    render.render_characters()
    render.render_matchup_data()
    render.render_player_details()
    render.render_scales()


@yomi2.command()
@click.option("--min-games", default=0, type=int)
@click.option(
    "--model", type=click.Choice(list(MODELS.keys())), default="y2_full_glicko_no_scale"
)
@click.option("--warmup", type=int, default=500)
@click.option("--samples", type=int, default=1000)
def render(min_games, model, warmup, samples):
    y1_tournament_games = yomi.latest_tournament_games()
    y1_sirlin_games = yomi.sirlin_db()
    y1_games = pandas.concat([y1_tournament_games, y1_sirlin_games]).reset_index(
        drop=True
    )
    y1_games = yomi.augment_dataset(y1_games)

    y2_games = games_yomi2.latest_tournament_games()
    y2_games = yomi.augment_dataset(y2_games)

    pipeline = (
        MODELS[model]
        .pipeline(
            rating_periods__player__kw_args=dict(field_prefix="player", threshold=1),
            rating_periods__player_character__kw_args=dict(
                field_prefix="player_character", threshold=3
            ),
            transform__glicko__initial_time=pandas.concat(
                [y1_games, y2_games]
            ).match_date.min(),
            transform__pc_glicko__initial_time=pandas.concat(
                [y1_games, y2_games]
            ).match_date.min(),
            model__min_games=min_games,
            model__warmup=warmup,
            model__samples=samples,
            # transform__elo__default_k=16,
            # transform__pc_elo__default_k=1,
            transform__glicko__initial_value=(1500.0, 50, 0.059),
            transform__pc_glicko__initial_value=(1500.0, 40, 0.027),
            # transform__elo__rating_factor=1135.77,  # 200-point rating difference corresponds to 60% win chance
            verbose=True,
            prefit_games=y1_games,
        )
        .fit(y2_games, y2_games.win)
    )

    render = YomiRender(pipeline, "src-js/data/yomi2")
    render.render_aggregate_skill()
    render.render_players()
    render.render_characters()
    render.render_matchup_data()
    render.render_player_details()
    render.render_scales()
    render.render_gem_effects()


if __name__ == "__main__":
    cli()
