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


def extract_index(col_name):
    field, _, rest = col_name.partition("[")
    indices = [int(idx) for idx in rest[:-1].split(",")]
    return field, indices


class YomiRender:
    def __init__(self, model: YomiModel):
        self.model = model

    def render_matchup_comparator(self, game, dest, static_root="."):
        os.makedirs(f"site/{game}/playerData", exist_ok=True)
        orig_players = self.model.data_.min_games__player_1_orig.dtype.categories.values
        public_games = self.model.data_[self.model.data_.render__public]
        public_players = pandas.concat(
            [
                public_games.min_games__player_1_orig,
                public_games.min_games__player_2_orig,
            ]
        ).unique()
        print(f"Computing per-player data for {len(public_players)} players")
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

            with open(f"site/{game}/playerData/{player}.json", "w") as outfile:
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

        print("Computing matchup dict")
        matchup_dict = defaultdict(dict)
        import pprint

        pprint.pprint(self.model.inf_data_["posterior"].mu.mean(["chain", "draw"]))

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
                    "mean": 1 - round(float(mu_means.loc[matchup]), 3),
                    "std": round(float(mu_std.loc[matchup]), 3),
                    "counts": len(
                        self.model.data_.loc[
                            (self.model.data_.matchup__character_1 == c2)
                            & (self.model.data_.matchup__character_2 == c1)
                        ]
                    ),
                }

        with open(f"site/{game}/matchupData.json", "w") as outfile:
            json.dump(matchup_dict, outfile, indent=2, sort_keys=True)

        print("Computing player skill")

        elo_by_player = pandas.concat(
            [
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_1_orig",
                        "elo__r1",
                        "pc_elo__r1",
                    ]
                ].rename(
                    columns={
                        "min_games__player_1_orig": "player",
                        "elo__r1": "elo_before",
                        "pc_elo__r1": "pc_elo_before",
                    }
                ),
                self.model.data_[
                    [
                        "render__match_date",
                        "min_games__player_2_orig",
                        "elo__r2",
                        "pc_elo__r2",
                    ]
                ].rename(
                    columns={
                        "min_games__player_2_orig": "player",
                        "elo__r2": "elo_before",
                        "pc_elo__r2": "pc_elo_before",
                    }
                ),
            ]
        )
        player_elo = (
            elo_by_player.sort_values(["render__match_date"]).groupby("player").last()
        ).dropna()

        player_game_counts = (
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
        ).dropna()

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

        player_data = defaultdict(dict)
        for player in public_players:
            for (
                character
            ) in self.model.data_.matchup__character_1.dtype.categories.values:
                player_data[player][character] = {
                    "played": int(player_character_counts[player].get(character, 0)),
                }

        for player in public_players:
            player_data[player]["elo"] = round(player_elo.loc[player, "elo_before"], 0)
            player_data[player]["pc_elo"] = round(
                player_elo.loc[player, "pc_elo_before"], 0
            )
            player_data[player]["gamesPlayed"] = int(player_game_counts[player])

        with open(f"site/{game}/playerSkill.json", "w") as outfile:
            json.dump(player_data, outfile, indent=2, sort_keys=True)

        templates = TemplateLookup(directories=["templates"])

        with open(f"site/{game}/characters.json", "w") as outfile:
            json.dump(
                list(self.model.data_.matchup__character_1.dtype.categories.values),
                outfile,
                indent=2,
                sort_keys=True,
            )

        with open(f"site/{game}/scales.json", "w") as outfile:
            json.dump(
                {
                    "elo_scale_main": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.mean(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "elo_scale_std": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.std(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "elo_scale_main": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.mean(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "elo_scale_std": round(
                        float(
                            self.model.inf_data_["posterior"].elo_scale.std(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                },
                outfile,
                indent=2,
                sort_keys=True,
            )

        with open(dest, "w") as outfile:
            outfile.write(
                templates.get_template(f"{game}.html").render_unicode(
                    has_versions=False, static_root=static_root
                )
            )

        return dest
