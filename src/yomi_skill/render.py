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
    def __init__(self, data_name, model: YomiModel):
        self.model = model
        self.data_name = data_name

    @property
    def base_folder(self):
        base_folder = f"images/{self.data_name}/{self.model.model_name}-{self.model.model_hash[:6]}"
        os.makedirs(base_folder, exist_ok=True)
        return base_folder

    def render_matchup_comparator(self, game="yomi", dest=None, static_root="."):
        os.makedirs(f"site/{game}/playerData", exist_ok=True)
        orig_players = sorted(
            set(
                pandas.unique(
                    pandas.concat(
                        [self.model.games.player_1_orig, self.model.games.player_2_orig]
                    )
                )
            )
        )
        for player in orig_players:
            p1_games = self.model.games[
                (self.model.games.player_1_orig == player)
            ].rename(
                columns={
                    col: (
                        col.replace("player_2_orig", "opponent")
                        .replace("player_1_orig", "player")
                        .replace("_1", "_p")
                        .replace("_2", "_o")
                    )
                    for col in self.model.games.columns
                }
            )
            p2_games = self.model.games[
                (self.model.games.player_2_orig == player)
            ].rename(
                columns={
                    col: (
                        col.replace("player_1_orig", "opponent")
                        .replace("player_2_orig", "player")
                        .replace("_2", "_p")
                        .replace("_1", "_o")
                    )
                    for col in self.model.games.columns
                }
            )
            p2_games.win = ~p2_games.win

            with open(f"site/{game}/playerData/{player}.json", "w") as outfile:
                json.dump(
                    json.loads(
                        pandas.concat([p1_games, p2_games])
                        .sort_values("match_date")
                        .to_json(orient="records", double_precision=3)
                    ),
                    outfile,
                    indent=2,
                    sort_keys=True,
                )

        matchup_dict = defaultdict(dict)

        mu_means = self.model.fit["posterior"].mu.mean(["chain", "draw"])
        mu_std = self.model.fit["posterior"].mu.std(["chain", "draw"])

        for c1, c2 in self.model.mu_list:
            matchup_dict[c1][c2] = {
                "mean": round(float(mu_means.loc[f"{c1}-{c2}"]), 3),
                "std": round(float(mu_std.loc[f"{c1}-{c2}"]), 3),
                "counts": len(
                    self.model.games.loc[
                        (self.model.games.character_1 == c1)
                        & (self.model.games.character_2 == c2)
                    ]
                ),
            }
            if c1 != c2:
                matchup_dict[c2][c1] = {
                    "mean": 1 - round(float(mu_means.loc[f"{c1}-{c2}"]), 3),
                    "std": round(float(mu_std.loc[f"{c1}-{c2}"]), 3),
                    "counts": len(
                        self.model.games.loc[
                            (self.model.games.character_1 == c2)
                            & (self.model.games.character_2 == c1)
                        ]
                    ),
                }

        player_char_skill_mean = self.model.fit["posterior"].char_skill.mean(
            ["chain", "draw"]
        )
        player_char_skill_std = self.model.fit["posterior"].char_skill.std(
            ["chain", "draw"]
        )

        elo_by_player = pandas.concat(
            [
                self.model.games[
                    ["match_date", "player_1_orig", "elo_before_1"]
                ].rename(
                    columns={"player_1_orig": "player", "elo_before_1": "elo_before"}
                ),
                self.model.games[
                    ["match_date", "player_2_orig", "elo_before_2"]
                ].rename(
                    columns={"player_2_orig": "player", "elo_before_2": "elo_before"}
                ),
            ]
        )
        player_elo = (
            elo_by_player.sort_values(["match_date"])
            .groupby("player")
            .elo_before.last()
        ).dropna()

        player_game_counts = (
            pandas.concat(
                [
                    self.model.games.player_1_orig.rename("player"),
                    self.model.games.player_2_orig.rename("player"),
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
                    self.model.games[["player_1_orig", "character_1"]].rename(
                        columns={"player_1_orig": "player", "character_1": "character"}
                    ),
                    self.model.games[["player_2_orig", "character_2"]].rename(
                        columns={"player_2_orig": "player", "character_2": "character"}
                    ),
                ]
            )
            .groupby(["player", "character"])
            .size()
        ).dropna()

        player_data = defaultdict(dict)
        for player in orig_players:
            for character in self.model.characters:
                play_counts = player_game_counts.loc[player]
                model_player = (
                    player
                    if play_counts > self.model.min_games
                    else self.model.min_games_player
                )
                mean = player_char_skill_mean.sel(
                    player=model_player,
                    character=character,
                )
                std = player_char_skill_std.sel(
                    player=model_player,
                    character=character,
                )
                player_data[player][character] = {
                    "mean": round(float(mean), 3),
                    "std": round(float(std), 3),
                    "played": int(player_character_counts[player].get(character, 0)),
                }
        for player, elo in player_elo.items():
            player_data[player]["elo"] = round(elo, 0)
        for player, count in player_game_counts.items():
            player_data[player]["gamesPlayed"] = count

        templates = TemplateLookup(directories=["templates"])

        outfile_name = f"{self.base_folder}/matchup-comparator.html"

        if game == "yomi":
            characters = [
                "Grave",
                "Midori",
                "Rook",
                "Valerie",
                "Lum",
                "Jaina",
                "Setsuki",
                "DeGrey",
                "Geiger",
                "Argagarg",
                "Quince",
                "BBB",
                "Menelker",
                "Gloria",
                "Vendetta",
                "Onimaru",
                "Troq",
                "Persephone",
                "Gwen",
                "Zane",
            ]
        else:
            characters = self.model.characters

        with open(f"site/{game}/matchupData.json", "w") as outfile:
            json.dump(matchup_dict, outfile, indent=2, sort_keys=True)

        with open(f"site/{game}/characters.json", "w") as outfile:
            json.dump(list(characters), outfile, indent=2, sort_keys=True)

        with open(f"site/{game}/playerSkill.json", "w") as outfile:
            json.dump(player_data, outfile, indent=2, sort_keys=True)

        with open(f"site/{game}/eloScale.json", "w") as outfile:
            json.dump(
                {
                    "mean": round(
                        float(
                            self.model.fit["posterior"].elo_logit_scale.mean(
                                ["chain", "draw"]
                            )
                        ),
                        3,
                    ),
                    "std": round(
                        float(
                            self.model.fit["posterior"].elo_logit_scale.std(
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

        with open(outfile_name, "w") as outfile:
            outfile.write(
                templates.get_template(f"{game}.html").render_unicode(
                    has_versions=False, static_root=static_root
                )
            )

        if dest is not None:
            shutil.copyfile(outfile_name, dest)

        return outfile_name
