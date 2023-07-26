from IPython.core.display import display
from plotnine import *
from functools import cached_property
import os
from colorsys import hsv_to_rgb
import matplotlib.colors
import math
import json
from collections import defaultdict
import pandas
import shutil
from mako.lookup import TemplateLookup
from .model import YomiModel
from sklearn.pipeline import Pipeline


def extract_index(col_name):
    field, _, rest = col_name.partition("[")
    indices = [int(idx) for idx in rest[:-1].split(",")]
    return field, indices


class YomiRender:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.model = pipeline["model"]

    def render_matchup_comparator(self, data_root):
        player_data_folder = f"{data_root}/player"
        orig_players = self.model.data_.min_games__player_1_orig.dtype.categories.values
        public_games = self.model.data_[self.model.data_.render__public]
        public_players = pandas.concat(
            [
                public_games.min_games__player_1_orig,
                public_games.min_games__player_2_orig,
            ]
        ).unique()
        print(f"Computing per-player data for {len(public_players)} players")

        player_character_counts = (
            pandas.concat(
                [
                    self.model.data_[
                        ["min_games__player_1_orig", "matchup__character_1"]
                    ].rename(
                        columns={
                            "min_games__player_1_orig": "player",
                            "matchup__character_1": "character",
                        }
                    ),
                    self.model.data_[
                        ["min_games__player_2_orig", "matchup__character_2"]
                    ].rename(
                        columns={
                            "min_games__player_2_orig": "player",
                            "matchup__character_2": "character",
                        }
                    ),
                ]
            )
            .groupby(["player", "character"])
            .size()
        ).dropna()

        elo_by_player = pandas.concat(
            [
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_1_orig",
                        "elo__r1",
                    ]
                ].rename(
                    columns={
                        "min_games__player_1_orig": "player",
                        "elo__r1": "elo_before",
                    }
                ),
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_2_orig",
                        "elo__r2",
                    ]
                ].rename(
                    columns={
                        "min_games__player_2_orig": "player",
                        "elo__r2": "elo_before",
                    }
                ),
            ]
        )
        player_elo = (
            elo_by_player.sort_values(["render__match_date"]).groupby("player").last()
        )

        elo_by_pc = pandas.concat(
            [
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_1_orig",
                        "matchup__character_1",
                        "pc_elo__r1",
                    ]
                ].rename(
                    columns={
                        "min_games__player_1_orig": "player",
                        "matchup__character_1": "character",
                        "pc_elo__r1": "pc_elo_before",
                    }
                ),
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_2_orig",
                        "matchup__character_2",
                        "pc_elo__r2",
                    ]
                ].rename(
                    columns={
                        "min_games__player_2_orig": "player",
                        "matchup__character_2": "character",
                        "pc_elo__r2": "pc_elo_before",
                    }
                ),
            ]
        )
        player_character_elo = (
            elo_by_pc.sort_values(["render__match_date"])
            .groupby(["player", "character"])
            .last()
        ).fillna(1500.0)

        player_game_counts = (
            (
                pandas.concat(
                    [
                        self.model.data_.min_games__player_1_orig.rename("player"),
                        self.model.data_.min_games__player_2_orig.rename("player"),
                    ]
                )
                .to_frame()
                .groupby("player")
                .size()
                .astype(int)
            )
            .loc[public_players]
            .dropna()
        )
        display(player_game_counts)

        for player in public_players:
            p1_games = public_games[
                (public_games.min_games__player_1_orig == player)
            ].rename(
                columns={
                    col: (
                        col.replace("min_games__player_2_orig", "opponent")
                        .replace("min_games__player_1_orig", "player")
                        .replace("_1", "_p")
                        .replace("_2", "_o")
                    )
                    for col in public_games.columns
                }
            )
            p2_games = public_games[
                (public_games.min_games__player_2_orig == player)
            ].rename(
                columns={
                    col: (
                        col.replace("min_games__player_1_orig", "opponent")
                        .replace("min_games__player_2_orig", "player")
                        .replace("_2", "_p")
                        .replace("_1", "_o")
                    )
                    for col in public_games.columns
                }
            )
            p2_games.render__win = ~p2_games.render__win

            player_folder = f"{player_data_folder}/{player}"
            os.makedirs(player_folder, exist_ok=True)
            with open(f"{player_folder}/history.json", "w") as outfile:
                json.dump(
                    json.loads(
                        pandas.concat([p1_games, p2_games])
                        .sort_values("render__match_date")
                        .to_json(orient="records", double_precision=3)
                    ),
                    outfile,
                    indent=2,
                    sort_keys=True,
                )

            with open(f"{player_folder}/skill.json", "w") as outfile:
                json.dump(
                    {
                        "char": {
                            character: {
                                "played": int(
                                    player_character_counts[player].get(character, 0)
                                ),
                                "elo": round(
                                    player_character_elo.loc[
                                        player, character
                                    ].pc_elo_before,
                                    0,
                                ),
                            }
                            for character in self.model.data_.matchup__character_1.dtype.categories.values
                        },
                        "elo": round(player_elo.loc[player].elo_before or 1500.0, 0),
                        "gamesPlayed": int(player_game_counts[player]),
                    },
                    outfile,
                    indent=2,
                    sort_keys=True,
                )

        print("Computing matchup dict")
        matchup_dict = defaultdict(dict)
        mu_means = self.model.inf_data_["posterior"].mu.mean(["chain", "draw"])
        mu_std = self.model.inf_data_["posterior"].mu.std(["chain", "draw"])

        for matchup in self.model.data_.matchup__mup.dtype.categories.values:
            c1, c2 = matchup.split("-")
            matchup_dict[c1][c2] = {
                "mean": round(float(mu_means.loc[matchup]), 3),
                "std": round(float(mu_std.loc[matchup]), 3),
                "counts": len(
                    self.model.data_.loc[
                        (self.model.data_.matchup__character_1 == c1)
                        & (self.model.data_.matchup__character_2 == c2)
                    ]
                ),
            }
            if c1 != c2:
                matchup_dict[c2][c1] = {
                    "mean": -matchup_dict[c1][c2]["mean"],
                    "std": matchup_dict[c1][c2]["std"],
                    "counts": matchup_dict[c1][c2]["counts"],
                }

        with open(f"{data_root}/matchupData.json", "w") as outfile:
            json.dump(matchup_dict, outfile, indent=2, sort_keys=True)

        print("Computing player skill")

        quantiles = [0.05, 0.25, 0.5, 0.75, 0.95, 1]
        character_elo = player_character_elo.groupby("character").pc_elo_before
        character_elo_qs = character_elo.quantile(quantiles)
        character_elo_std = character_elo.std()
        player_elo_qs = player_elo.dropna().elo_before.quantile(quantiles)
        player_elo_std = player_elo.dropna().elo_before.std()
        with open(f"{data_root}/playerSkill.json", "w") as outfile:
            json.dump(
                {
                    "elo": {
                        "qs": player_elo_qs.to_dict(),
                        "std": player_elo_std,
                    },
                    "char_elo_q": {
                        character: {
                            "qs": character_elo_qs.loc[character].to_dict(),
                            "std": character_elo_std.loc[character],
                        }
                        for character in self.model.data_.matchup__character_1.dtype.categories.values
                    },
                },
                outfile,
                indent=2,
                sort_keys=True,
            )

        with open(f"{data_root}/players.json", "w") as outfile:
            json.dump(
                player_game_counts.to_dict(),
                outfile,
                indent=2,
                sort_keys=True,
            )

        with open(f"{data_root}/characters.json", "w") as outfile:
            json.dump(
                list(self.model.data_.matchup__character_1.dtype.categories.values),
                outfile,
                indent=2,
                sort_keys=True,
            )

        with open(f"{data_root}/scales.json", "w") as outfile:
            json.dump(
                {
                    "eloScaleMean": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.mean(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "eloScaleStd": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.std(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "pcEloScaleMean": round(
                        float(
                            self.model.inf_data_["posterior"].pc_elo_scale.mean(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "pcEloScaleStd": round(
                        float(
                            self.model.inf_data_["posterior"].pc_elo_scale.std(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "eloFactor": self.pipeline["transform"]
                    .named_transformers_["elo"]
                    .rating_factor
                    or 400.0,
                    "pcEloFactor": self.pipeline["transform"]
                    .named_transformers_["pc_elo"]
                    .rating_factor
                    or 400.0,
                },
                outfile,
                indent=2,
                sort_keys=True,
            )
