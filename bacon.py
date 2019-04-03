import os
import pandas
from bacon_replay_analyzer import Replay
import logging
from collections import defaultdict
from datetime import datetime
from IPython.core.display import display
from games import normalize_types
from datetime import datetime


def load_replay_results(replay_dir):
    try:
        results = pandas.read_parquet(f"{replay_dir}/results.parquet")
    except:
        results = pandas.DataFrame(
            columns=[
                "replay",
                "match_date",
                "player_1",
                "character_1",
                "player_2",
                "character_2",
                "win",
            ]
        )

    available_replays = set(
        fname
        for fname in os.listdir(replay_dir)
        if "inject" not in fname and fname.endswith(".bcr")
    )
    cached_replays = set(results.replay)
    new_replays = available_replays - cached_replays

    records = []
    for replay_file in new_replays:
        try:
            replay = Replay(f"{replay_dir}/{replay_file}")

            records.append(
                {
                    "replay": replay.name,
                    "match_date": replay.match_date,
                    "player_1": replay.player_0,
                    "character_1": replay.fighter_0.name,
                    "player_2": replay.player_1,
                    "character_2": replay.fighter_1.name,
                    "win": replay.winner == replay.player_0,
                    "player_1_wins": replay.record_0[0],
                    "player_1_losses": replay.record_0[1],
                    "player_1_ties": replay.record_0[2],
                    "player_2_wins": replay.record_1[0],
                    "player_2_losses": replay.record_1[1],
                    "player_2_ties": replay.record_1[2],
                }
                if replay.fighter_0.name <= replay.fighter_1.name
                else {
                    "replay": replay.name,
                    "match_date": replay.match_date,
                    "player_1": replay.player_1,
                    "character_1": replay.fighter_1.name,
                    "player_2": replay.player_0,
                    "character_2": replay.fighter_0.name,
                    "win": replay.winner == replay.player_1,
                    "player_1_wins": replay.record_1[0],
                    "player_1_losses": replay.record_1[1],
                    "player_1_ties": replay.record_1[2],
                    "player_2_wins": replay.record_0[0],
                    "player_2_losses": replay.record_0[1],
                    "player_2_ties": replay.record_0[2],
                }
            )
        except:
            logging.exception(f"Unable to understand {replay_dir}/{replay_file}")
    results = results.append(pandas.DataFrame.from_records(records))

    if len(results) == 0:
        print(f"No replays found in {replay_dir}")
        return results

    display(results)
    results["submitter"] = (
        results.player_1.append(results.player_2).value_counts().index[0]
    )

    results.to_parquet(f"{replay_dir}/results.parquet", compression="gzip")
    return results[(results.player_1 != "Bot") & (results.player_2 != "Bot")]


def load_tankbard(record_file):
    records = pandas.read_csv(
        record_file,
        names=[
            "timestamp",
            "player_1",
            "character_1",
            "record_1",
            "win",
            "player_2",
            "character_2",
            "record_2",
        ],
    )
    records["timestamp"] = records.timestamp.astype(int)
    records["match_date"] = records.timestamp.apply(datetime.fromtimestamp)
    records["win"] = records.win.map({">": True, "<": False})
    records["submitter"] = "tankbard"
    records["replay"] = record_file

    backwards_mus = records.character_1 > records.character_2
    records[backwards_mus] = records[backwards_mus].rename(
        columns={
            "player_1": "player_2",
            "player_2": "player_1",
            "character_1": "character_2",
            "character_2": "character_1",
            "record_1": "record_2",
            "record_2": "record_1",
        }
    )
    records.loc[backwards_mus, ["win"]] = ~records[backwards_mus].win

    records["player_1_wins"] = records.record_1.apply(lambda r: int(r.split("-")[0]))
    records["player_1_losses"] = records.record_1.apply(lambda r: int(r.split("-")[1]))
    records["player_1_ties"] = records.record_1.apply(lambda r: int(r.split("-")[2]))
    records["player_2_wins"] = records.record_2.apply(lambda r: int(r.split("-")[0]))
    records["player_2_losses"] = records.record_2.apply(lambda r: int(r.split("-")[1]))
    records["player_2_ties"] = records.record_2.apply(lambda r: int(r.split("-")[2]))

    return records[(records.player_1 != "Aliphant") & (records.player_2 != "Aliphant")]


BASE_VERSION = "0.15"
VERSION_HISTORY = [
    (datetime(2018, 9, 19, 15), "0.16", ["Luc", "Kallistar"]),
    (datetime(2018, 10, 3), "0.17", ["Burman", "Hikaru", "Rukyuk", "Sarafina"]),
    (datetime(2018, 11, 15, 13), "0.18", ["Evil Hikaru"]),
    (
        datetime(2018, 12, 19, 17),
        "0.19",
        ["Iri", "Burman", "Magdelina", "Kimbhe", "Sarafina", "Seven"],
    ),
    (datetime(2019, 1, 30), "0.20", ["Rexan"]),
    (datetime(2019, 3, 6, 19), "0.21", ["Kehrolyn", "Seven"]),
    (datetime(2019, 3, 7, 19), "0.21a", ["Seven"]),
]


def apply_versions(games):
    games["version_1"] = BASE_VERSION
    games["version_2"] = BASE_VERSION
    for (version_date, version_name, chars) in VERSION_HISTORY:
        games.loc[
            games.character_1.isin(chars) & (games.match_date >= version_date),
            "version_1",
        ] = version_name
        games.loc[
            games.character_2.isin(chars) & (games.match_date >= version_date),
            "version_2",
        ] = version_name

    return games


INITIAL_ELO = 1500
LOW_K = 51
HIGH_K = 79
K_CUTOFF = 186
MIN_GAMES = 0
DENOM = 1135.77


def compute_elo(historical_records, low_k=LOW_K, high_k=HIGH_K, k_cutoff=K_CUTOFF):
    current_elo = defaultdict(lambda: INITIAL_ELO)
    play_counts = defaultdict(int)

    elo_records = []

    for row in historical_records.itertuples():
        rating1 = current_elo[row.player_1]
        rating2 = current_elo[row.player_2]
        q1 = pow(10, rating1 / DENOM)
        q2 = pow(10, rating2 / DENOM)
        expected1 = q1 / (q1 + q2)
        expected2 = q2 / (q1 + q2)
        gamesPlayed = 1
        wins1 = row.win
        wins2 = 1 - row.win
        played1 = play_counts[row.player_1]
        played2 = play_counts[row.player_2]
        k1 = high_k if played1 < k_cutoff else low_k
        k2 = high_k if played2 < k_cutoff else low_k
        newRating1 = rating1 + k1 * (wins1 - expected1 * gamesPlayed)
        newRating2 = rating2 + k2 * (wins2 - expected2 * gamesPlayed)

        record = {
            "elo_before_1": rating1,
            "elo_before_2": rating2,
            "games_played_1": play_counts[row.player_1],
            "games_played_2": play_counts[row.player_2],
        }

        play_counts[row.player_1] += 1
        play_counts[row.player_2] += 1

        current_elo[row.player_1] = newRating1
        current_elo[row.player_2] = newRating2

        record["elo_after_1"] = newRating1
        record["elo_after_2"] = newRating2
        record["elo_delta_1"] = newRating1 - rating1
        record["elo_delta_2"] = newRating2 - rating2
        elo_records.append(record)

    return historical_records.join(pandas.DataFrame.from_records(elo_records))


def display_elo_checks(games):
    enough_data = games
    enough_data["points_diff"] = enough_data.elo_before_1 - enough_data.elo_before_2
    enough_data["win_chance"] = 1 / (1 + (-enough_data.points_diff / 1135.77).rpow(10))
    squared_error = (
        (enough_data.win_chance - enough_data.win).pow(2)
        + ((1 - enough_data.win_chance) - (1 - enough_data.win)).pow(2)
    ).sum()

    enough_data["points_diff"] = (
        enough_data.elo_before_1 - enough_data.elo_before_2
    ).abs()
    enough_data["expected_win"] = (
        enough_data.elo_before_1 > enough_data.elo_before_2
    ) == enough_data.win
    enough_data["points_bin"] = (enough_data.points_diff / 50).round() * 50

    print("Elo Check")
    binned = (
        enough_data.groupby("points_bin")
        .expected_win.agg(["sum", "count"])
        .reset_index()
    )
    binned["expected_win_rate"] = 1 / (1 + (-binned.points_bin / 1135.77).rpow(10))
    binned["actual_win_rate"] = binned["sum"] / binned["count"]
    display(binned)

    print("squared error", squared_error)


def load_historical_record(replay_dir="../bacon-replays"):
    historical_record = pandas.DataFrame()
    with os.scandir(replay_dir) as it:
        historical_record = pandas.concat(
            load_replay_results(entry.path) for entry in it if entry.is_dir()
        )

    historical_record = historical_record.append(
        load_tankbard(replay_dir + "/bc_records")
    )

    historical_record["player_1_games_played"] = (
        historical_record.player_1_wins
        + historical_record.player_1_losses
        + historical_record.player_1_ties
    )
    historical_record["player_2_games_played"] = (
        historical_record.player_2_wins
        + historical_record.player_2_losses
        + historical_record.player_2_ties
    )

    historical_record["match_day"] = historical_record.match_date.apply(
        lambda d: d.isocalendar()
    )

    # historical_record = historical_record[(historical_record.player_1_games_played != 0) | (historical_record.player_2_games_played != 0)]

    historical_record = (
        historical_record.drop_duplicates(
            subset=[
                "match_day",
                "player_1",
                "player_2",
                "character_1",
                "character_2",
                "player_1_wins",
                "player_1_losses",
                "player_1_ties",
                "player_2_wins",
                "player_2_losses",
                "player_2_ties",
            ]
        )
        .sort_values(["match_date"])
        .reset_index(drop=True)
    )
    historical_record = historical_record.drop(columns=["match_day"])

    return historical_record


def games(replay_dir="../bacon-replays", autodata=None):
    game_dir = "games/bacon"
    os.makedirs(game_dir, exist_ok=True)
    cached = sorted(os.listdir(game_dir))
    if autodata == "same":
        pick = len(cached) - 1
    elif autodata == "new":
        pick = None
    else:
        print("\n".join("{}: {}".format(*choice) for choice in enumerate(cached)))
        pick = input("Load game data:")

    print("Pick", pick)
    games = None
    if pick:
        picked = cached[int(pick)]
        name, _ = os.path.splitext(picked)
        try:
            games = pandas.read_parquet(f"{game_dir}/{picked}")
        except:
            logging.exception("Can't load %s as parquet", picked)

    if games is None:
        historical_record = load_historical_record(replay_dir)

        with_versions = apply_versions(historical_record)

        display(with_versions)
        games = compute_elo(with_versions)

        name = str(datetime.now().isoformat())
        games.to_parquet(f"{game_dir}/{name}.parquet", compression="gzip")

    games = normalize_types(games)
    display_elo_checks(games)
    # display(games[games.isna().any(axis=1)])
    return os.path.join("bacon", name), games
