import os
import pandas
from bacon_replay_analyzer import Replay
import logging
from collections import defaultdict
from datetime import datetime
from IPython.core.display import display
from games import normalize_types


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
                }
            )
        except:
            logging.exception(f"Unable to understand {replay_dir}/{replay_file}")
    results = results.append(pandas.DataFrame.from_records(records))

    results.to_parquet(f"{replay_dir}/results.parquet", compression="gzip")
    return results[(results.player_1 != "Bot") & (results.player_2 != "Bot")]


INITIAL_ELO = 1500
LOW_K = 25
HIGH_K = 125
K_CUTOFF = 95
MIN_GAMES = 0
DENOM = 1135.77


def compute_elo(historical_records, low_k=LOW_K, high_k=HIGH_K, k_cutoff=K_CUTOFF):
    historical_records = historical_records.sort_values(["match_date"]).reset_index(
        drop=True
    )
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

        elo_records.append(
            {
                "elo_before_1": rating1,
                "elo_before_2": rating2,
                "games_played_1": play_counts[row.player_1],
                "games_played_2": play_counts[row.player_2],
            }
        )

        play_counts[row.player_1] += 1
        play_counts[row.player_2] += 1

        current_elo[row.player_1] = newRating1
        current_elo[row.player_2] = newRating2

    return historical_records.join(pandas.DataFrame.from_records(elo_records))


def display_elo_checks(games):
    enough_data = games[
        (games.games_played_1 > MIN_GAMES) & (games.games_played_2 > MIN_GAMES)
    ]
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


def games(replay_dir="../bacon-replays"):
    game_dir = "games/bacon"
    os.makedirs(game_dir, exist_ok=True)
    cached = sorted(os.listdir(game_dir))
    print("\n".join("{}: {}".format(*choice) for choice in enumerate(cached)))
    pick = input("Load game data:")
    games = None
    if pick:
        picked = cached[int(pick)]
        name, _ = os.path.splitext(picked)
        try:
            games = pandas.read_parquet(f"{game_dir}/{picked}")
        except:
            logging.exception("Can't load %s as parquet", picked)

    if games is None:
        historical_record = load_replay_results(replay_dir)
        games = compute_elo(historical_record)

        name = str(datetime.now().isoformat())
        games.to_parquet(f"{game_dir}/{name}.parquet", compression="gzip")

    games = normalize_types(games)
    display_elo_checks(games)
    display(games[games.isna().any(axis=1)])
    return os.path.join("bacon", name), games.dropna()
