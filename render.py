from IPython.core.display import display
from plotnine import *
from cached_property import cached_property
import os
from colorsys import hsv_to_rgb
import matplotlib.colors
import math
import json
from collections import defaultdict
import pandas


def extract_index(col_name):
    field, _, rest = col_name.partition("[")
    indices = [int(idx) for idx in rest[:-1].split(",")]
    return field, indices


class YomiRender:
    def __init__(self, data_name, model, warmup=1000, min_samples=1000):
        self.model = model
        self.warmup = warmup
        self.min_samples = min_samples
        self.base_folder = (
            f"images/{data_name}/{self.model.model_name}-{self.model.model_hash[:6]}"
        )
        os.makedirs(self.base_folder, exist_ok=True)

    @property
    def results_df(self):
        return self.model.sample_dataframe(
            warmup=self.warmup, min_samples=self.min_samples
        )

    @cached_property
    def player_category(self):
        return pandas.api.types.CategoricalDtype(
            self.model.player_index.keys(), ordered=True
        )

    @cached_property
    def player_tournament_skill(self):
        results = self.results_df
        reverse_player_tournament_index = {
            ix: (player, tournament)
            for ((player, tournament), ix) in self.model.player_tournament_index.items()
        }

        tournament_category = pandas.api.types.CategoricalDtype(
            self.model.tournament_index.keys(), ordered=True
        )

        player_tournament_skill = (
            results[[col for col in results.columns if col.startswith("skill[")]]
            .unstack()
            .rename("skill")
            .reset_index()
        )
        player_tournament_skill["player"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][0]
        ).astype(self.player_category)
        player_tournament_skill["tournament"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[int(x[6:-1])][1]
        ).astype(tournament_category)

        del (player_tournament_skill["level_0"])
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

        tournament_category = pandas.api.types.CategoricalDtype(
            self.model.tournament_index.keys(), ordered=True
        )

        player_tournament_skill = (
            results[[col for col in results.columns if col.startswith("raw_skill[")]]
            .unstack()
            .rename("raw_skill")
            .reset_index()
        )
        player_tournament_skill["player"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][0]
        ).astype(self.player_category)
        player_tournament_skill["tournament"] = player_tournament_skill.level_0.apply(
            lambda x: reverse_player_tournament_index[extract_index(x)[1][0]][1]
        ).astype(tournament_category)

        del (player_tournament_skill["level_0"])
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
    def player_char_skill(self):
        results = self.results_df
        reverse_player_index = {
            ix: player for (player, ix) in self.model.player_index.items()
        }
        reverse_character_index = {
            ix: char for (char, ix) in self.model.character_index.items()
        }

        player_char_skill = (
            results[[col for col in results.columns if col.startswith("char_skill[")]]
            .unstack()
            .rename("char_skill")
            .reset_index()
        )
        player_char_skill["player"] = player_char_skill.level_0.apply(
            lambda x: reverse_player_index[int(x[11:-1].split(",")[1])]
        ).astype(self.player_category)
        player_char_skill["character"] = player_char_skill.level_0.apply(
            lambda x: reverse_character_index[int(x[11:-1].split(",")[0])]
        ).astype(character_category)

        del (player_char_skill["level_0"])
        player_char_skill = player_char_skill.rename(columns={"level_1": "sample"})

        sample_max_skill = player_char_skill.groupby("sample").char_skill.max()
        for sample in player_char_skill["sample"].unique():
            player_char_skill.loc[
                player_char_skill["sample"] == sample, "char_skill"
            ] -= sample_max_skill[sample]

        player_char_skill["win_chance"] = pandas.to_numeric(
            (player_char_skill["char_skill"].rpow(math.e))
            / (1 + player_char_skill["char_skill"].rpow(math.e))
        )
        return player_char_skill

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
        display(self.raw_player_tournament_skill.player.unique())
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
        skill = self.player_char_skill
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
        skill = self.player_char_skill
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

    @cached_property
    def matchups(self):
        fit_results = self.results_df
        mu_index = self.model.mu_index

        matchups = (
            fit_results[[col for col in fit_results.columns if col.startswith("mu[")]]
            .rename(
                columns={
                    "mu[{}]".format(ix): "{.value}-{.value}".format(c1, c2)
                    for ((c1, c2), ix) in mu_index.items()
                }
            )
            .unstack()
            .rename("win_rate")
            .reset_index()
        )
        matchups["c1"] = matchups.level_0.apply(
            lambda x: x.split("-")[0]
        ).astype(character_category)
        matchups["c2"] = matchups.level_0.apply(
            lambda x: x.split("-")[1]
        ).astype(character_category)
        matchups["win_rate"] = pandas.to_numeric(matchups["win_rate"])
        del (matchups["level_0"])
        matchups = matchups.rename(columns={"level_1": "sample"})

        flipped = matchups[matchups.c1 != matchups.c2].rename(
            columns={"c1": "c2", "c2": "c1"}
        )
        flipped["win_rate"] = -flipped["win_rate"]

        matchups = matchups.append(flipped)

        matchups["win_rate"] = pandas.to_numeric(
            10
            * (matchups["win_rate"].rpow(math.e))
            / (1 + matchups["win_rate"].rpow(math.e))
        )
        return matchups

    def render_matchup_chart(self):
        median_rates = pandas.to_numeric(
            self.matchups.groupby(["c1", "c2"])
            .win_rate.median()
            .rename("median_win_rate")
        )
        text_color = median_rates.reset_index().median_win_rate.apply(
            lambda x: "white" if x > 6 or x < 4 else "black"
        )

        matchups = self.matchups.join(median_rates, on=["c1", "c2"])

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
        median_win_rate = self.matchups.groupby(["c1", "c2"]).win_rate.median()
        abs_unbalance = (median_win_rate - 5).abs().rename("abs_unbalance")
        most_balanced = (
            abs_unbalance.reset_index()
            .sort_values(["c1", "abs_unbalance"])
            .groupby("c1")
            .head(6)
        )

        display(most_balanced.set_index(["c1", "c2"]).join(median_win_rate))

        lines = []
        lines.append("| Character | Counterpick |")
        lines.append("|---|---|")
        for character in Character:
            counterpicks = " ".join(
                most_balanced[most_balanced.c1 == character].c2.apply(
                    lambda c: f":{c}:"
                )
            )
            lines.append(f"|:{character}:|{counterpicks}|")

        return "\n".join(lines)

    def render_matchup_comparator(self):
        summary = self.model.summary_dataframe(self.warmup, self.min_samples)

        mu_index = self.model.mu_index

        matchups = (
            summary[[col for col in summary.columns if col.startswith("mu[")]]
            .rename(
                columns={
                    "mu[{}]".format(ix): "{}-{}".format(c1, c2)
                    for ((c1, c2), ix) in mu_index.items()
                }
            )
            .transpose()
            .reset_index()
        )
        matchups["c1"] = matchups["index"].apply(
            lambda x: x.split("-")[0]
        )
        matchups["c2"] = matchups["index"].apply(
            lambda x: x.split("-")[1]
        )
        del matchups["index"]

        flipped = matchups[matchups.c1 != matchups.c2].rename(
            columns={"c1": "c2", "c2": "c1"}
        )
        flipped["mean"] = -flipped["mean"]

        matchups = matchups.append(flipped).sort_values(["c1", "c2"])

        reverse_player_index = {
            ix: player for (player, ix) in self.model.player_index.items()
        }
        reverse_character_index = {
            ix: char for (char, ix) in self.model.character_index.items()
        }

        player_char_skill = (
            summary[[col for col in summary.columns if col.startswith("char_skill[")]]
            .transpose()
            .reset_index()
        )
        player_char_skill["player"] = (
            player_char_skill["index"]
            .apply(lambda x: reverse_player_index[int(x[11:-1].split(",")[1])])
            .astype(self.player_category)
        )
        player_char_skill["character"] = player_char_skill["index"].apply(
            lambda x: reverse_character_index[int(x[11:-1].split(",")[0])]
        )

        del (player_char_skill["index"])

        player_elo = (
            self.model.games[["match_date", "player_1", "elo_before_1"]]
            .rename(columns={"player_1": "player", "elo_before_1": "elo_before"})
            .append(
                self.model.games[["match_date", "player_2", "elo_before_2"]].rename(
                    columns={"player_2": "player", "elo_before_2": "elo_before"}
                )
            )
            .sort_values(["match_date"])
            .groupby("player")
            .elo_before.last()
        )

        player_data = defaultdict(dict)
        for row in player_char_skill.itertuples():
            player_data[row.player][row.character] = {"mean": row.mean, "std": row.std}
        for player, elo in player_elo.items():
            player_data[player]["elo"] = elo

        with open("matchup-comparator-template.html") as template_file:
            template = template_file.read()

        outfile_name = f"{self.base_folder}/matchup-comparator.html"
        with open(outfile_name, "w") as outfile:
            outfile.write(
                template.replace("$MATCHUP_DATA", matchups.to_json(orient="records"))
                .replace("$CHARACTERS", json.dumps([c for c in self.model.characters]))
                .replace("$PLAYER_SKILL", json.dumps(player_data))
                .replace(
                    "$ELO_SCALE",
                    json.dumps(
                        {
                            "mean": summary.elo_logit_scale["mean"],
                            "std": summary.elo_logit_scale["std"],
                        }
                    ),
                )
            )
        return outfile_name
