import logging
import os
import re
from collections import defaultdict
from datetime import datetime

import sqlite3
import numpy as np
import pandas
from skelo.model.glicko2 import Glicko2Estimator
from skelo.model.elo import EloEstimator

from .character import character_category, Character

HISTORICAL_GSHEET = "https://docs.google.com/spreadsheets/u/1/d/1HcdISgCl3s4RpWkJa8m-G1JjfKzd8qf2WY2Xcw32D7U/export?format=csv&id=1HcdISgCl3s4RpWkJa8m-G1JjfKzd8qf2WY2Xcw32D7U&gid=1371955398"
ELO_GSHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR5wMDB9AXwmC8N1UEcbbkNNbCcUdnhOmsFRyrXCU8huErk20zKeULEVdAidCijMUc678oOC1F7tgUI/pub?gid=1688184901&single=true&output=csv"


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

    known_chars = [char.value for char in Character]

    historical_record = historical_record[
        historical_record.character_1.apply(lambda v: v.lower()).isin(known_chars)
        & historical_record.character_2.apply(lambda v: v.lower()).isin(known_chars)
    ]

    historical_record["match_date"] = pandas.to_datetime(historical_record.match_date)
    historical_record.set_win_1 = historical_record.set_win_1.fillna(0)
    historical_record.set_win_2 = historical_record.set_win_2.fillna(0)
    historical_record.wins_1 = historical_record.wins_1.fillna(0)
    historical_record.wins_2 = historical_record.wins_2.fillna(0)

    historical_record.character_1 = historical_record.character_1.apply(
        lambda c: c.lower()
    ).astype(character_category)
    historical_record.character_2 = historical_record.character_2.apply(
        lambda c: c.lower()
    ).astype(character_category)

    historical_record = normalize_players(historical_record)

    historical_record = historical_record.astype(
        {
            "set_win_1": "int8",
            "wins_1": "int8",
            "wins_2": "int8",
            "set_win_2": "int8",
        }
    )

    return historical_record


def fetch_historical_elo(url=ELO_GSHEET):
    historical_elo = pandas.read_csv(url)
    historical_elo.columns = [
        re.sub("\W+", "_", col.lower()).strip("_") for col in historical_elo.columns
    ]
    historical_elo = historical_elo[
        [
            "set_number",
            "event",
            "match_date",
            "elo_1_before",
            "elo_1_after",
            "set_win_1",
            "player_1",
            "player_2",
            "set_win_2",
            "elo_2_before",
            "elo_2_after",
        ]
    ]
    historical_elo = historical_elo.dropna(
        subset=["event", "player_1", "player_2", "match_date"]
    )

    name_map = fetch_name_map()

    historical_elo.match_date = pandas.to_datetime(
        historical_elo.match_date, infer_datetime_format=True
    )
    historical_elo.set_win_1 = historical_elo.set_win_1.fillna(0)
    historical_elo.set_win_2 = historical_elo.set_win_2.fillna(0)

    historical_elo = historical_elo[
        historical_elo.player_1.apply(lambda v: v.lower()).isin(name_map.index)
        & historical_elo.player_2.apply(lambda v: v.lower()).isin(name_map.index)
    ]

    historical_elo.player_1 = historical_elo.player_1.apply(
        lambda n: name_map.loc[n.lower()]
    )
    historical_elo.player_2 = historical_elo.player_2.apply(
        lambda n: name_map.loc[n.lower()]
    )

    player_category = pandas.api.types.CategoricalDtype(
        sorted(
            pandas.concat([historical_elo.player_1, historical_elo.player_2]).unique()
        ),
        ordered=True,
    )

    tournament_category = pandas.api.types.CategoricalDtype(
        sorted(historical_elo.event.unique()), ordered=True
    )
    historical_elo = historical_elo.astype(
        {
            "set_number": int,
            "event": tournament_category,
            "elo_1_before": float,
            "elo_1_after": float,
            # 'sets_played_1': int,
            "set_win_1": "int8",
            "player_1": player_category,
            "player_2": player_category,
            "set_win_2": "int8",
            "elo_2_before": float,
            "elo_2_after": float,
            # 'sets_played_2': int,
            # '5_elo': float,
            # '25_elo': float,
            # '50_elo': float,
            # '75_elo': float,
            # '95_elo': float,
        }
    )

    return historical_elo


def as_player_elo(historical_elo):
    p1_elo = historical_elo[
        ["set_number", "event", "match_date", "elo_1_before", "elo_1_after", "player_1"]
    ].rename(
        columns={
            "player_1": "player",
            "elo_1_before": "elo_before",
            "elo_1_after": "elo_after",
        }
    )
    p2_elo = historical_elo[
        ["set_number", "event", "match_date", "elo_2_before", "elo_2_after", "player_2"]
    ].rename(
        columns={
            "player_2": "player",
            "elo_2_before": "elo_before",
            "elo_2_after": "elo_after",
        }
    )

    all_player_elo = pandas.concat([p1_elo, p2_elo])
    all_player_elo.loc[:, "elo_before"].fillna(1500, inplace=True)
    all_player_elo.loc[:, "elo_after"].fillna(1500, inplace=True)
    return all_player_elo.set_index(["set_number", "player"])


def as_boolean_win_record(historical_record):
    p1_wins = historical_record.loc[
        np.repeat(historical_record.index.values, historical_record.wins_1.astype(int))
    ].reset_index(drop=True)
    p2_wins = historical_record.loc[
        np.repeat(historical_record.index.values, historical_record.wins_2.astype(int))
    ].reset_index(drop=True)

    p1_wins["win"] = 1
    p2_wins["win"] = 0

    games = pandas.concat([p1_wins, p2_wins]).reset_index(drop=True)[
        [
            "match_date",
            "player_1",
            "character_1",
            "win",
            "character_2",
            "player_2",
        ]
    ]

    games = games.astype({"win": "int8"})
    return games.sort_values(["match_date"])


def latest_tournament_games() -> pandas.DataFrame:
    game_dir = "games/yomi"
    name = str(datetime.now().isoformat())
    historical_record = fetch_historical_record()
    historical_record = as_boolean_win_record(historical_record)
    historical_record.to_parquet(f"{game_dir}/{name}.parquet", compression="gzip")
    return historical_record


def cached_tournament_games() -> pandas.DataFrame:
    game_dir = "games/yomi"
    cached = sorted(os.listdir(game_dir))
    pick = len(cached) - 1
    picked = cached[int(pick)]
    name, _ = os.path.splitext(picked)
    return pandas.read_parquet(f"{game_dir}/{picked}")


def parse_game_results(result):
    if result.endswith("dc"):
        return None
    return {"0": None, "1": 1, "2": 0}[result[0]]


def sirlin_db() -> pandas.DataFrame:
    con = sqlite3.connect("yomi_results_ranked_2013-06-15_to_2015-09-07.sqlite")
    df = pandas.read_sql_query("SELECT * from yomi_results", con)
    char_map = {
        0: Character.Grave.value,
        1: Character.Jaina.value,
        2: Character.Midori.value,
        3: Character.Setsuki.value,
        4: Character.Rook.value,
        5: Character.DeGrey.value,
        6: Character.Valerie.value,
        7: Character.Geiger.value,
        8: Character.Lum.value,
        9: Character.Argagarg.value,
        10: Character.Quince.value,
        11: Character.Onimaru.value,
        12: Character.Troq.value,
        13: Character.BBB.value,
        14: Character.Menelker.value,
        15: Character.Persephone.value,
        16: Character.Gloria.value,
        17: Character.Gwen.value,
        18: Character.Vendetta.value,
        19: Character.Zane.value,
    }
    return (
        normalize_players(
            pandas.DataFrame(
                {
                    "player_1": df.p1name,
                    "player_2": df.p2name,
                    "character_1": df.p1char.astype("int")
                    .map(char_map)
                    .astype(character_category),
                    "character_2": df.p1char.astype("int")
                    .map(char_map)
                    .astype(character_category),
                    "win": df.result.map(parse_game_results),
                    "match_date": pandas.to_datetime(df.start_time),
                }
            )
        )
        .dropna()
        .astype({"win": "int8"})
    )


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

    print("Estimating player glicko")
    player_glicko_model = Glicko2Estimator(
        key1_field="player_1",
        key2_field="player_2",
        timestamp_field="match_date",
        initial_time=games.match_date.min(),
    ).fit(games, games.win)
    # player_glicko_ratings = player_glicko_model.transform(games, output_type="rating")

    print("Estimating player Elo")
    player_elo_model = EloEstimator(
        key1_field="player_1",
        key2_field="player_2",
        timestamp_field="match_date",
        initial_time=games.match_date.min(),
    ).fit(games, games.win)
    player_elo_ratings = player_elo_model.transform(games, output_type="rating")

    print("Estimating player-character glick")
    player_character_glicko_model = Glicko2Estimator(
        key1_field="player_character_1",
        key2_field="player_character_2",
        timestamp_field="match_date",
        initial_time=games.match_date.min(),
    ).fit(games, games.win)
    # pc_glicko_ratings = player_character_glicko_model.transform(
    #     games, output_type="rating"
    # )

    print("Estimating player-character Elo")
    player_character_elo_model = EloEstimator(
        key1_field="player_character_1",
        key2_field="player_character_2",
        timestamp_field="match_date",
        initial_time=games.match_date.min(),
    ).fit(games, games.win)
    pc_elo_ratings = player_character_elo_model.transform(games, output_type="rating")

    games["elo_1"] = player_elo_ratings.r1
    games["elo_2"] = player_elo_ratings.r2
    games["pc_elo_1"] = pc_elo_ratings.r1
    games["pc_elo_2"] = pc_elo_ratings.r2
    games["glicko_estimate"] = player_glicko_model.predict_proba(games).pr1
    games["pc_glicko_estimate"] = player_character_glicko_model.predict_proba(games).pr1
    games["elo_estimate"] = player_elo_model.predict_proba(games).pr1
    games["pc_elo_estimate"] = player_elo_model.predict_proba(games).pr1
    games.sort_values("match_date", inplace=True)
    return games
