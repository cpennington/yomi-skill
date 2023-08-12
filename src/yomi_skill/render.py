import json
import os
import re
from collections import defaultdict
from typing import List

import pandas
import simplejson
from IPython.core.display import display
from sklearn.pipeline import Pipeline
from functools import cached_property


def extract_index(col_name):
    field, _, rest = col_name.partition("[")
    indices = [int(idx) for idx in rest[:-1].split(",")]
    return field, indices


class YomiRender:
    def __init__(self, pipeline: Pipeline, data_root):
        self.pipeline = pipeline
        self.model = pipeline["model"]
        self.data_root = data_root

    @cached_property
    def public_games(self):
        return self.model.data_[self.model.data_.render__public]

    @cached_property
    def public_players(self):
        return pandas.concat(
            [
                self.public_games.min_games__player_1_orig,
                self.public_games.min_games__player_2_orig,
            ]
        ).unique()

    @cached_property
    def player_character_counts(self):
        return (
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

    @cached_property
    def player_character_ratings_history(self):
        return self.rating_by_pc.sort_values(["render__match_date"]).groupby(
            ["player", "character"]
        )

    @cached_property
    def player_character_ratings_devs(self):
        return (
            {
                (player, character): pandas.concat(
                    [pandas.Series([0]), matches["pc_elo"]]
                )
                .rolling(50, min_periods=0)
                .std()
                .iloc[-1]
                for (
                    player,
                    character,
                ), matches in self.player_character_ratings_history
            }
            if "pc_elo" in self.rating_by_pc.columns
            else {}
        )

    @cached_property
    def rating_by_pc(self):
        return pandas.concat(
            [
                self.ratings_data[
                    [
                        "render__match_date",
                        "min_games__player_1_orig",
                        "matchup__character_1",
                        "pc_elo__r1",
                        "pc_glicko__r1",
                        "pc_glicko__rd1",
                        "pc_glicko__v1",
                    ]
                ].rename(
                    columns={
                        "min_games__player_1_orig": "player",
                        "matchup__character_1": "character",
                        "pc_elo__r1": "pc_elo",
                        "pc_glicko__r1": "pc_glicko_r",
                        "pc_glicko__rd1": "pc_glicko_rd",
                        "pc_glicko__v1": "pc_glicko_v",
                    }
                ),
                self.ratings_data[
                    [
                        "render__match_date",
                        "min_games__player_2_orig",
                        "matchup__character_2",
                        "pc_elo__r2",
                        "pc_glicko__r2",
                        "pc_glicko__rd2",
                        "pc_glicko__v2",
                    ]
                ].rename(
                    columns={
                        "min_games__player_2_orig": "player",
                        "matchup__character_2": "character",
                        "pc_elo__r2": "pc_elo",
                        "pc_glicko__r2": "pc_glicko_r",
                        "pc_glicko__rd2": "pc_glicko_rd",
                        "pc_glicko__v2": "pc_glicko_v",
                    }
                ),
            ]
        )

    @cached_property
    def ratings_data(self):
        rating_columns = [
            "elo__r1",
            "elo__r2",
            "glicko__r1",
            "glicko__r2",
            "glicko__rd1",
            "glicko__rd2",
            "glicko__v1",
            "glicko__v2",
            "matchup__character_1",
            "matchup__character_2",
            "gem__with_gem_1",
            "gem__against_gem_1",
            "gem__with_gem_2",
            "gem__against_gem_2",
            "min_games__player_1_orig",
            "min_games__player_2_orig",
            "pc_elo__r1",
            "pc_elo__r2",
            "pc_glicko__r1",
            "pc_glicko__r2",
            "pc_glicko__rd1",
            "pc_glicko__rd2",
            "pc_glicko__v1",
            "pc_glicko__v2",
            "render__match_date",
        ]
        return self.model.data_.reindex(columns=rating_columns, fill_value=None)

    @cached_property
    def player_game_counts(self):
        return (
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
            .loc[self.public_players]
            .dropna()
        )

    @cached_property
    def top_glicko_by_character(self):
        return {
            character: [
                {
                    "player": player,
                    "r": round(row.pc_glicko_r, 2),
                    "rd": round(row.pc_glicko_rd, 2),
                    "v": round(row.pc_glicko_v, 3),
                }
                for (player, _), row in pc_ratings.sort_values(
                    "pc_glicko_r", ascending=False
                )
                .head(20)
                .iterrows()
            ]
            for character, pc_ratings in self.player_character_ratings_history.last()
            .loc[self.public_players, :]
            .dropna(subset=["pc_glicko_r"])
            .groupby("character")
        }

    @cached_property
    def player_character_ratings(self):
        return self.player_character_ratings_history.last().fillna(
            value={
                **(
                    {
                        "pc_elo": (self.pc_elo_transformer.initial_value or 1500.0),
                    }
                    if self.pc_elo_transformer
                    else {}
                ),
                **(
                    {
                        "pc_glicko_r": (
                            self.pc_glicko_transformer.initial_value[0] or 1500.0
                        ),
                        "pc_glicko_rd": (
                            self.pc_glicko_transformer.initial_value[1] or 350
                        ),
                        "pc_glicko_v": (
                            self.pc_glicko_transformer.initial_value[2] or 0.06
                        ),
                    }
                    if self.pc_glicko_transformer
                    else {}
                ),
            }
        )

    @cached_property
    def rating_by_player(self):
        return pandas.concat(
            [
                self.ratings_data[
                    [
                        "render__match_date",
                        "min_games__player_1_orig",
                        "elo__r1",
                        "glicko__r1",
                        "glicko__rd1",
                        "glicko__v1",
                    ]
                ].rename(
                    columns={
                        "min_games__player_1_orig": "player",
                        "elo__r1": "elo",
                        "glicko__r1": "glicko_r",
                        "glicko__rd1": "glicko_rd",
                        "glicko__v1": "glicko_v",
                    }
                ),
                self.ratings_data[
                    [
                        "render__match_date",
                        "min_games__player_2_orig",
                        "elo__r2",
                        "glicko__r2",
                        "glicko__rd2",
                        "glicko__v2",
                    ]
                ].rename(
                    columns={
                        "min_games__player_2_orig": "player",
                        "elo__r2": "elo",
                        "glicko__r2": "glicko_r",
                        "glicko__rd2": "glicko_rd",
                        "glicko__v2": "glicko_v",
                    }
                ),
            ]
        )

    @cached_property
    def player_ratings_history(self):
        return self.rating_by_player.sort_values(["render__match_date"]).groupby(
            "player"
        )

    @cached_property
    def player_ratings_devs(self):
        return (
            {
                player: pandas.concat([pandas.Series([0]), matches["elo"]])
                .rolling(30, min_periods=1)
                .std()
                .iloc[-1]
                for player, matches in self.player_ratings_history
            }
            if "elo" in self.rating_by_player.columns
            else {}
        )

    @cached_property
    def player_ratings(self):
        return self.player_ratings_history.last().fillna(
            value={
                **(
                    {"elo": (self.elo_transformer.initial_value or 1500.0)}
                    if self.elo_transformer
                    else {}
                ),
                **(
                    {
                        "glicko_r": (
                            self.glicko_transformer.initial_value[0] or 1500.0
                        ),
                        "glicko_rd": (self.glicko_transformer.initial_value[1] or 350),
                        "glicko_v": (self.glicko_transformer.initial_value[2] or 0.06),
                    }
                    if self.glicko_transformer
                    else {}
                ),
            }
        )

    @cached_property
    def elo_transformer(self):
        return self.pipeline["transform"].named_transformers_.get("elo")

    @cached_property
    def glicko_transformer(self):
        return self.pipeline["transform"].named_transformers_.get("glicko")

    @cached_property
    def pc_elo_transformer(self):
        return self.pipeline["transform"].named_transformers_.get("pc_elo")

    @cached_property
    def pc_glicko_transformer(self):
        return self.pipeline["transform"].named_transformers_.get("pc_glicko")

    def render_scales(self):
        col_means = self.model.inf_data_["posterior"].mean(["chain", "draw"])
        col_std = self.model.inf_data_["posterior"].std(["chain", "draw"])

        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/scales.json", "w") as outfile:
            simplejson.dump(
                {
                    **{
                        re.sub(r"_\w", lambda m: m[0][1].upper(), column)
                        + "Mean": round(float(col_means[column]), 3)
                        for column in col_means.data_vars.keys()
                        if column.endswith("scale")
                    },
                    **{
                        re.sub(r"_\w", lambda m: m[0][1].upper(), column)
                        + "Std": round(float(col_std[column]), 3)
                        for column in col_std.data_vars.keys()
                        if column.endswith("scale")
                    },
                    **(
                        {"eloFactor": self.elo_transformer.rating_factor or 400}
                        if self.elo_transformer
                        else {}
                    ),
                    **(
                        {"pcEloFactor": self.pc_elo_transformer.rating_factor or 400}
                        if self.pc_elo_transformer
                        else {}
                    ),
                },
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )

    def render_player_details(self):
        print(f"Computing per-player data for {len(self.public_players)} players")
        for player in self.public_players:
            p1_games = self.public_games[
                (self.public_games.min_games__player_1_orig == player)
            ].rename(
                columns={
                    col: re.sub(
                        r"([12])$",
                        lambda p: {"2": "o", "1": "p"}[p[1]],
                        col.replace("min_games__player_2_orig", "opponent").replace(
                            "min_games__player_1_orig", "player"
                        ),
                    )
                    for col in self.public_games.columns
                }
            )
            p2_games = self.public_games[
                (self.public_games.min_games__player_2_orig == player)
            ].rename(
                columns={
                    col: re.sub(
                        r"([12])$",
                        lambda p: {"1": "o", "2": "p"}[p[1]],
                        col.replace("min_games__player_1_orig", "opponent").replace(
                            "min_games__player_2_orig", "player"
                        ),
                    )
                    for col in self.public_games.columns
                }
            )
            p2_games.render__win = 1 - p2_games.render__win

            player_folder = f"{self.data_root}/player/{player}"
            os.makedirs(player_folder, exist_ok=True)
            with open(f"{player_folder}/history.json", "w") as outfile:
                simplejson.dump(
                    json.loads(
                        pandas.concat([p1_games, p2_games])
                        .sort_values("render__match_date")
                        .to_json(orient="records", double_precision=3)
                    ),
                    outfile,
                    indent=2,
                    sort_keys=True,
                    ignore_nan=True,
                )

            with open(f"{player_folder}/skill.json", "w") as outfile:
                simplejson.dump(
                    {
                        "char": {
                            character: {
                                "gamesPlayed": int(
                                    self.player_character_counts[player].get(
                                        character, 0
                                    )
                                ),
                                "elo": round(
                                    self.player_character_ratings.loc[
                                        player, character
                                    ].pc_elo,
                                    3,
                                ),
                                "elo_std": round(
                                    self.player_character_ratings_devs.get(
                                        (player, character), 1060
                                    ),
                                    3,
                                ),
                                "glickoR": round(
                                    self.player_character_ratings.loc[
                                        player, character
                                    ].pc_glicko_r,
                                    3,
                                ),
                                "glickoRD": round(
                                    self.player_character_ratings.loc[
                                        player, character
                                    ].pc_glicko_rd,
                                    3,
                                ),
                                "glickoV": round(
                                    self.player_character_ratings.loc[
                                        player, character
                                    ].pc_glicko_v,
                                    3,
                                ),
                            }
                            for character in self.model.data_.matchup__character_1.dtype.categories.values
                        },
                        "elo": round(self.player_ratings.loc[player].elo or 1500.0, 3),
                        "elo_std": round(self.player_ratings_devs.get(player, 1060), 3),
                        "glickoR": round(
                            self.player_ratings.loc[player].glicko_r,
                            3,
                        ),
                        "glickoRD": round(
                            self.player_ratings.loc[player].glicko_rd,
                            3,
                        ),
                        "glickoV": round(
                            self.player_ratings.loc[player].glicko_v,
                            3,
                        ),
                        "gamesPlayed": int(self.player_game_counts[player]),
                    },
                    outfile,
                    indent=2,
                    sort_keys=True,
                    ignore_nan=True,
                )

    def render_characters(self):
        character_counts = (
            pandas.concat(
                [
                    self.model.data_.matchup__character_1.rename("character"),
                    self.model.data_.matchup__character_2.rename("character"),
                ]
            )
            .to_frame()
            .groupby("character")
            .size()
        ).dropna()
        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/characters.json", "w") as outfile:
            simplejson.dump(
                [
                    {
                        "character": character,
                        "gamesRecorded": int(character_counts[character]),
                    }
                    for character in list(
                        self.model.data_.matchup__character_1.dtype.categories.values
                    )
                ],
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )

    def render_players(self):
        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/players.json", "w") as outfile:
            simplejson.dump(
                self.player_game_counts.to_dict(),
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )

    def render_aggregate_skill(self):
        print("Computing player skill")
        quantiles: List[float] = [0.05, 0.25, 0.5, 0.75, 0.95, 1]
        character_ratings = self.player_character_ratings.groupby("character")
        character_qs = character_ratings.quantile(quantiles, numeric_only=True)
        character_std = character_ratings.std()
        player_ratings_qs = self.player_ratings.dropna().quantile(
            quantiles, numeric_only=True
        )
        player_ratings_std = self.player_ratings.dropna().std()

        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/playerSkill.json", "w") as outfile:
            simplejson.dump(
                {
                    "globalSkill": {
                        "elo": {
                            "qs": player_ratings_qs.elo.to_dict(),
                            "std": player_ratings_std.elo,
                        },
                        "glicko": {
                            "r": {
                                "qs": player_ratings_qs.glicko_r.to_dict(),
                                "std": player_ratings_std.glicko_r,
                            },
                            "rd": {
                                "qs": player_ratings_qs.glicko_rd.to_dict(),
                                "std": player_ratings_std.glicko_rd,
                            },
                            "v": {
                                "qs": player_ratings_qs.glicko_v.to_dict(),
                                "std": player_ratings_std.glicko_v,
                            },
                        },
                    },
                    "characters": {
                        character: {
                            "elo": {
                                "qs": character_qs.pc_elo.loc[character].to_dict(),
                                "std": character_std.pc_elo.loc[character],
                            },
                            "glicko": {
                                "top20": self.top_glicko_by_character.get(
                                    character, []
                                ),
                                "r": {
                                    "qs": character_qs.pc_glicko_r.loc[
                                        character
                                    ].to_dict(),
                                    "std": character_std.pc_glicko_r.loc[character],
                                },
                                "rd": {
                                    "qs": character_qs.pc_glicko_rd.loc[
                                        character
                                    ].to_dict(),
                                    "std": character_std.pc_glicko_rd.loc[character],
                                },
                                "v": {
                                    "qs": character_qs.pc_glicko_v.loc[
                                        character
                                    ].to_dict(),
                                    "std": character_std.pc_glicko_v.loc[character],
                                },
                            },
                        }
                        for character in self.model.data_.matchup__character_1.dtype.categories.values
                    },
                },
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )

    def render_matchup_data(self):
        print("Computing matchup dict")
        matchup_dict = defaultdict(dict)
        mu_means = self.model.inf_data_["posterior"].mu.mean(["chain", "draw"])
        mu_std = self.model.inf_data_["posterior"].mu.std(["chain", "draw"])

        for matchup in self.model.data_.matchup__mup.dtype.categories.values:
            c1, c2 = matchup.split("-")
            matchup_dict[c1][c2] = {
                "mean": round(float(mu_means.loc[matchup]), 3),
                "std": round(float(mu_std.loc[matchup]), 3),
                "count": len(
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
                    "count": matchup_dict[c1][c2]["count"],
                }

        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/matchupData.json", "w") as outfile:
            simplejson.dump(
                matchup_dict,
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )

    def render_gem_effects(self):
        print("Computing matchup dict")
        with_gem_means = self.model.inf_data_["posterior"].with_gem.mean(
            ["chain", "draw"]
        )
        with_gem_std = self.model.inf_data_["posterior"].with_gem.std(["chain", "draw"])
        against_gem_means = self.model.inf_data_["posterior"].against_gem.mean(
            ["chain", "draw"]
        )
        against_gem_std = self.model.inf_data_["posterior"].against_gem.std(
            ["chain", "draw"]
        )

        gems = {"with_gem": defaultdict(dict), "against_gem": defaultdict(dict)}
        for with_gem in self.model.data_.gem__with_gem_1.dtype.categories.values:
            c, g = with_gem.split("-")
            gems["with_gem"][c][g] = {
                "mean": round(float(with_gem_means.loc[with_gem]), 3),
                "std": round(float(with_gem_std.loc[with_gem]), 3),
                "count": len(
                    self.model.data_.loc[
                        (
                            (self.model.data_.gem__character_1 == c)
                            & (self.model.data_.gem__gem_1 == g)
                        )
                        | (
                            (self.model.data_.gem__character_2 == c)
                            & (self.model.data_.gem__gem_2 == g)
                        )
                    ]
                ),
            }

        for against_gem in self.model.data_.gem__against_gem_1.dtype.categories.values:
            g, c = against_gem.split("-")
            gems["against_gem"][g][c] = {
                "mean": round(float(against_gem_means.loc[against_gem]), 3),
                "std": round(float(against_gem_std.loc[against_gem]), 3),
                "count": len(
                    self.model.data_.loc[
                        (
                            (self.model.data_.gem__character_2 == c)
                            & (self.model.data_.gem__gem_1 == g)
                        )
                        | (
                            (self.model.data_.gem__character_1 == c)
                            & (self.model.data_.gem__gem_2 == g)
                        )
                    ]
                ),
            }

        os.makedirs(self.data_root, exist_ok=True)
        with open(f"{self.data_root}/gemEffects.json", "w") as outfile:
            simplejson.dump(
                gems,
                outfile,
                indent=2,
                sort_keys=True,
                ignore_nan=True,
            )
