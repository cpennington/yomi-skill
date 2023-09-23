import os
import re
from datetime import datetime, time, timedelta
from enum import Enum

import pandas

from .yomi.character import Character, character_category


class Gem(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    Blue = "blue"
    Red = "red"
    White = "white"
    Black = "black"
    Purple = "purple"
    Green = "green"

    def __str__(self):
        return self.name


for gem in Gem:
    locals()[gem.name] = gem

gem_category = pandas.api.types.CategoricalDtype(
    [gem.value for gem in Gem], ordered=True
)


HISTORICAL_GSHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSCLtJnpmI1d9j46OG6sWes2Pto7snpEW5IzG3JsAC0JtLMu18-hTqWGj1SVT2NGRqEPRniyHDyWMPD/pub?gid=0&single=true&output=csv"


def normalize_players(games: pandas.DataFrame):
    all_players = (
        pandas.concat([games.player_1, games.player_2]).rename("player").to_frame()
    )
    all_players["normalized"] = all_players.player.apply(
        lambda v: re.sub(r"[^a-z0-9]", "", v.lower())
    )

    player_map = all_players.groupby("normalized").player.agg(
        lambda x: pandas.Series.mode(x)[0]
    )

    all_players["standardized"] = all_players.normalized.apply(lambda p: player_map[p])
    all_players = all_players.drop_duplicates().set_index(["player"])

    games.player_1 = games.player_1.apply(lambda p: all_players.standardized[p])
    games.player_2 = games.player_2.apply(lambda p: all_players.standardized[p])

    player_category = pandas.api.types.CategoricalDtype(
        sorted(pandas.concat([games.player_1, games.player_2]).unique()),
        ordered=True,
    )
    return games.astype({"player_1": player_category, "player_2": player_category})


def order_by_character(games):
    backwards_mus = games.character_1 > games.character_2
    games.loc[backwards_mus] = games[backwards_mus].rename(
        columns={
            "player_1": "player_2",
            "player_2": "player_1",
            "character_1": "character_2",
            "character_2": "character_1",
            "gem_1": "gem_2",
            "gem_2": "gem_1",
        }
    )
    games.loc[backwards_mus, ["win"]] = 1 - games[backwards_mus].win

    mirror_mus_to_flip = list(
        games[games.character_1 == games.character_2].iloc[::2].index.values
    )
    games.iloc[mirror_mus_to_flip] = games.iloc[mirror_mus_to_flip].rename(
        columns={
            "player_1": "player_2",
            "player_2": "player_1",
            "character_1": "character_2",
            "character_2": "character_1",
            "gem_1": "gem_2",
            "gem_2": "gem_1",
        }
    )
    games.iloc[mirror_mus_to_flip, games.columns.get_loc("win")] = (
        1 - games.iloc[mirror_mus_to_flip].win
    )
    return games


def fetch_name_map(url=HISTORICAL_GSHEET):
    historical_record = pandas.read_csv(url)
    historical_record.columns = [
        re.sub("\W+", "_", col.lower()).strip("_") for col in historical_record.columns
    ]

    known_chars = [char.value for char in Character]
    historical_record = historical_record[
        historical_record.character_1.apply(lambda v: v.lower()).isin(known_chars)
        & historical_record.character_2.apply(lambda v: v.lower()).isin(known_chars)
    ]

    names = pandas.DataFrame(
        {
            "name": pandas.concat(
                [historical_record.player_1, historical_record.player_2]
            )
        }
    )
    names["lower"] = names.apply(lambda r: r["name"].lower(), axis=1)
    name_map = names.groupby("lower").first()
    return name_map


def fetch_historical_record(url=HISTORICAL_GSHEET):
    historical_record = pandas.read_csv(url)
    historical_record.columns = [
        re.sub("\W+", "_", col.lower()).strip("_") for col in historical_record.columns
    ]

    historical_record.loc[
        historical_record.character_1 == "DragonMidori", "character_1"
    ] = "Midori"
    historical_record.loc[
        historical_record.character_2 == "DragonMidori", "character_2"
    ] = "Midori"

    known_chars = [char.value for char in Character]

    historical_record = historical_record[
        historical_record.character_1.apply(lambda v: v.lower()).isin(known_chars)
        & historical_record.character_2.apply(lambda v: v.lower()).isin(known_chars)
    ]

    historical_record["match_date"] = pandas.to_datetime(
        historical_record.match_date, errors="coerce", utc=True
    )

    historical_record.character_1 = historical_record.character_1.apply(
        lambda c: c.lower()
    ).astype(character_category)
    historical_record.character_2 = historical_record.character_2.apply(
        lambda c: c.lower()
    ).astype(character_category)

    historical_record.gem_1 = historical_record.gem_1.apply(lambda c: c.lower()).astype(
        gem_category
    )
    historical_record.gem_2 = historical_record.gem_2.apply(lambda c: c.lower()).astype(
        gem_category
    )

    historical_record = normalize_players(historical_record)

    historical_record["win"] = historical_record.winner == "P1"

    match_has_date_only = historical_record.match_date.dt.time == time(0, 0)
    date_matches = historical_record[match_has_date_only]
    datetime_matches = historical_record[~match_has_date_only].copy()
    datetime_matches["cluster"] = (
        datetime_matches.match_date.sort_values()
        .diff()
        .gt(timedelta(minutes=1))
        .cumsum()
        .add(1)
    )

    datetime_matches = datetime_matches.drop_duplicates(
        [
            "cluster",
            "player_1",
            "player_2",
            "gem_1",
            "gem_2",
            "character_1",
            "character_2",
        ]
    ).drop(columns="cluster")

    return pandas.concat([date_matches, datetime_matches]).sort_values("match_date")


def latest_tournament_games() -> pandas.DataFrame:
    game_dir = "games/yomi2"
    name = str(datetime.now().isoformat())
    historical_record = fetch_historical_record()
    historical_record["public"] = True
    os.makedirs(game_dir, exist_ok=True)
    print(historical_record)
    historical_record.to_parquet(f"{game_dir}/{name}.parquet", compression="gzip")
    return historical_record


def cached_tournament_games() -> pandas.DataFrame:
    game_dir = "games/yomi2"
    cached = sorted(os.listdir(game_dir))
    pick = len(cached) - 1
    picked = cached[int(pick)]
    name, _ = os.path.splitext(picked)
    return pandas.read_parquet(f"{game_dir}/{picked}")


def augment_dataset(games):
    games = order_by_character(games)
    games = normalize_players(games)
    games.dropna(inplace=True)
    print("Constructing PC category")
    games["player_character_1"] = games.apply(
        lambda r: f"{r.player_1}-{r.character_1}", axis=1
    ).astype("category")
    games["player_character_2"] = games.apply(
        lambda r: f"{r.player_2}-{r.character_2}", axis=1
    ).astype("category")

    games["match_date"] = games.match_date.dt.normalize()
    games.sort_values("match_date", inplace=True)
    return games
