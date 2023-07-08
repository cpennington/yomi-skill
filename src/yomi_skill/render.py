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

    @property
    def results_df(self):
        return self.model.sample_dataframe

    @cached_property
    def player_tournament_skill(self):
        results = self.results_df
        reverse_player_tournament_index = {
            ix: (player, tournament)
            for ((player, tournament), ix) in self.model.player_tournament_index.items()
        }

        player_tournament_skill = (
            results[[col for col in results.columns if col.startswith("skill[")]]
            .unstack()
            .rename("skill")
            .reset_index()
        )
        player_tournament_skill["player"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][0]
        ).astype("category")
        player_tournament_skill["tournament"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][1]
        ).astype("category")

        del player_tournament_skill["level_0"]
        player_tournament_skill = player_tournament_skill.rename(
            columns={"level_1": "sample"}
        )
        tournament_list = (
            self.model.games.groupby("tournament_name")
            .match_date.quantile(0.5)
            .sort_values()
            .index.tolist()
        )

        player_tournament_skill["tournament"] = player_tournament_skill[
            "tournament"
        ].cat.reorder_categories(tournament_list, ordered=True)
        return player_tournament_skill

    @cached_property
    def raw_player_tournament_skill(self):
        results = self.results_df
        reverse_player_tournament_index = {
            ix: (player, tournament)
            for ((player, tournament), ix) in self.model.player_tournament_index.items()
        }

        player_tournament_skill = (
            results[[col for col in results.columns if col.startswith("raw_skill[")]]
            .unstack()
            .rename("raw_skill")
            .reset_index()
        )
        player_tournament_skill["player"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][0]
        ).astype("category")
        player_tournament_skill["tournament"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][1]
        ).astype("category")

        del player_tournament_skill["level_0"]
        player_tournament_skill = player_tournament_skill.rename(
            columns={"level_1": "sample"}
        )
        tournament_list = (
            self.model.games.groupby("tournament_name")
            .match_date.quantile(0.5)
            .sort_values()
            .index.tolist()
        )

        player_tournament_skill["tournament"] = player_tournament_skill[
            "tournament"
        ].cat.reorder_categories(tournament_list, ordered=True)
        return player_tournament_skill

    def render_player_skill(self, player):
        player_skill = self.player_tournament_skill[
            self.player_tournament_skill.player == player
        ]
        player_chart = (
            ggplot(player_skill, aes(x="tournament", y="skill"))
            + geom_violin()
            + geom_line(
                player_skill.groupby("tournament").median().reset_index().dropna()
            )
            + theme(
                figure_size=(player_skill.tournament.nunique() * 0.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
        )
        player_chart.save(f"{self.base_folder}/{player}-skill.png", verbose=False)

    def render_raw_player_skill(self, player):
        player_skill = self.raw_player_tournament_skill[
            self.raw_player_tournament_skill.player == player
        ]
        player_chart = (
            ggplot(player_skill, aes(x="tournament", y="raw_skill"))
            + geom_violin()
            + geom_line(
                player_skill.groupby("tournament").median().reset_index().dropna()
            )
            + theme(
                figure_size=(player_skill.tournament.nunique() * 0.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
        )
        player_chart.save(f"{self.base_folder}/{player}-raw-skill.png", verbose=False)

    def render_char_skill(self, player):
        skill = self.model.player_char_skill
        char_skill = skill[skill.player == player]
        skill_summaries = char_skill.groupby("character").char_skill.agg(
            ["median", "std"]
        )

        # def row_color(row):
        #     median_skill = skill_summaries['median'][row.character]
        #     median_skill_in_unit_range = (median_skill - min_skill_median) / (-min_skill_median)
        #     hue = median_skill_in_unit_range * (.33)

        #     skill_std = skill_summaries['std'][row.character]
        #     skill_std_in_unit_range = (max_skill_std - skill_std) / max_skill_std
        #     sat = 1 - skill_std_in_unit_range
        #     return matplotlib.colors.to_hex(hsv_to_rgb(hue, sat, 0.8))

        char_skill["skill_median"] = (
            char_skill.character.apply(lambda c: skill_summaries["median"][c]).astype(
                float
            )
            + 5
        )
        char_skill["skill_std"] = char_skill.character.apply(
            lambda c: skill_summaries["std"][c]
        ).astype(float)
        char_skill_chart = (
            ggplot(
                char_skill,
                aes(
                    x="character",
                    y="char_skill + 5",
                    fill="skill_median",
                    alpha="skill_std",
                ),
            )
            + geom_violin(scale="width")
            + scale_fill_distiller(type="div", palette="Spectral")
            + scale_alpha(range=(1, 0.2), limits=(0, 2))
            + theme(
                figure_size=(char_skill.character.nunique() * 0.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + labs(title=player)
            + ylim(0, 5)
        )
        char_skill_chart.save(
            f"{self.base_folder}/{player}-char-skill.png", verbose=False
        )

    def render_char_win_chance(self, player):
        skill = self.model.player_char_skill
        char_skill = skill[skill.player == player]
        skill_summaries = char_skill.groupby("character").win_chance.agg(
            ["median", "std"]
        )

        # def row_color(row):
        #     median_skill = skill_summaries['median'][row.character]
        #     median_skill_in_unit_range = (median_skill - min_skill_median) / (-min_skill_median)
        #     hue = median_skill_in_unit_range * (.33)

        #     skill_std = skill_summaries['std'][row.character]
        #     skill_std_in_unit_range = (max_skill_std - skill_std) / max_skill_std
        #     sat = 1 - skill_std_in_unit_range
        #     return matplotlib.colors.to_hex(hsv_to_rgb(hue, sat, 0.8))

        char_skill["skill_median"] = char_skill.character.apply(
            lambda c: skill_summaries["median"][c]
        ).astype(float)
        char_skill["skill_std"] = char_skill.character.apply(
            lambda c: skill_summaries["std"][c]
        ).astype(float)
        char_skill_chart = (
            ggplot(
                char_skill,
                aes(
                    x="character",
                    y="win_chance",
                    fill="skill_median",
                    alpha="skill_std",
                ),
            )
            + geom_violin(scale="width")
            + scale_fill_distiller(
                type="div",
                palette="Spectral",
                labels=lambda l: ["%d%%" % (v * 100) for v in l],
                limits=(0, 0.5),
            )
            + scale_alpha(range=(1, 0.2))
            + theme(
                figure_size=(char_skill.character.nunique() * 0.2, 2),
                axis_text_x=element_text(rotation=90),
            )
            + scale_y_continuous(
                labels=lambda l: ["%d%%" % (v * 100) for v in l], limits=(0, 0.5)
            )
            + labs(title=player)
        )
        char_skill_chart.save(
            f"{self.base_folder}/{player}-char-win-chance.png", verbose=False
        )

    def render_player_skills(self, *players):
        for player in players:
            self.render_player_skill(player)

    def render_raw_player_skills(self, *players):
        for player in players:
            self.render_raw_player_skill(player)

    def render_matchup_chart(self):
        median_rates = pandas.to_numeric(
            self.model.matchups.groupby(["c1", "c2"])
            .win_rate.median()
            .rename("median_win_rate")
        )
        text_color = median_rates.reset_index().median_win_rate.apply(
            lambda x: "white" if x > 6 or x < 4 else "black"
        )

        matchups = self.model.matchups.join(median_rates, on=["c1", "c2"])

        matchup_chart = (
            ggplot(matchups, aes(x="0", y="win_rate", fill="median_win_rate"))
            + geom_violin()
            + geom_text(
                data=median_rates.reset_index(),
                mapping=aes(label="median_win_rate", y="median_win_rate", x=0, size=9),
                color=text_color,
                format_string="{:.2}",
            )
            + facet_grid("c1 ~ c2")
            + coord_flip()
            + theme(figure_size=(25, 15))
            + scale_fill_gradient2(midpoint=5)
        )

        filename = f"{self.base_folder}/matchup-chart.png"
        matchup_chart.save(filename, verbose=False)

    def balanced_matchups(self):
        median_win_rate = (
            self.model.matchups[self.model.matchups.c1 != self.model.matchups.c2]
            .groupby(["c1", "c2"])
            .win_rate.median()
        )
        abs_unbalance = (median_win_rate - 5).abs().rename("abs_unbalance")
        most_balanced = (
            abs_unbalance.reset_index()
            .sort_values(["c1", "abs_unbalance"])
            .groupby("c1")
            .head(5)
        )

        display(most_balanced.set_index(["c1", "c2"]).join(median_win_rate))

        lines = []
        lines.append("| Character | Counterpick |")
        lines.append("|---|---|")
        for character in self.model.characters:
            counterpicks = " ".join(
                most_balanced[most_balanced.c1 == character].c2.apply(
                    lambda c: f":{c}:"
                )
            )
            lines.append(f"|:{character}:|{counterpicks}|")

        return "\n".join(lines)

    def render_matchup_comparator(self, game="yomi", dest=None, static_root="."):
        mu_index = self.model.mu_index

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
