import os
import pandas
from bacon_replay_analyzer import Replay
import logging
from collections import defaultdict
from datetime import datetime
from IPython.core.display import display

def load_replay_results(replay_dir):
    try:
        results = pandas.read_parquet(f"{replay_dir}/results.parquet")
    except:
        results = pandas.DataFrame(columns=['replay', 'match_date', 'player_1', 'character_1', 'player_2', 'character_2', 'win'])

    available_replays = set(fname for fname in os.listdir(replay_dir) if 'inject' not in fname and fname.endswith('.bcr'))
    print(available_replays)
    cached_replays = set(results.replay)
    print(cached_replays)
    new_replays = available_replays - cached_replays
    print(len(new_replays))

    records = []
    for replay_file in new_replays:
        try:
            replay = Replay(f'{replay_dir}/{replay_file}')

            records.append(
                {
                    'replay': replay.name,
                    'match_date': replay.match_date,
                    'player_1': replay.player_0,
                    'character_1': replay.fighter_0.name,
                    'player_2': replay.player_1,
                    'character_2': replay.fighter_1.name,
                    'win': replay.winner == replay.player_0
                } if replay.fighter_0.name <= replay.fighter_1.name else {
                    'replay': replay.name,
                    'match_date': replay.match_date,
                    'player_1': replay.player_1,
                    'character_1': replay.fighter_1.name,
                    'player_2': replay.player_0,
                    'character_2': replay.fighter_0.name,
                    'win': replay.winner == replay.player_1
                }
            )
        except:
            logging.exception(f"Unable to understand {replay_dir}/{replay_file}")
    results = results.append(pandas.DataFrame.from_records(records))

    all_chars = results.character_1.append(results.character_2).rename('character').to_frame()
    all_chars['lower'] = all_chars.character.apply(lambda v: v.lower())

    char_map = all_chars.groupby('lower').character.first()

    results.character_1 = results.character_1.apply(lambda c: char_map[c.lower()])
    results.character_2 = results.character_2.apply(lambda c: char_map[c.lower()])

    character_category = pandas.api.types.CategoricalDtype(sorted(set(results.character_1) | set(results.character_2)), ordered=True)

    results = results.astype({'character_1': character_category, 'character_2': character_category})
    results.to_parquet(f"{replay_dir}/results.parquet", compression='gzip')
    return results[(results.player_1 != 'Bot') & (results.player_2 != 'Bot')]

INITIAL_ELO = 1500
LOW_K = 8
HIGH_K = 16
K_CUTOFF = 50
DENOM = 1135.77

def compute_elo(historical_records):
    historical_records = historical_records.sort_values(['match_date']).reset_index(drop=True)
    current_elo = defaultdict(lambda: INITIAL_ELO)
    play_counts = defaultdict(int)

    elo_records = []

    for row in historical_records.itertuples():
        rating1 = current_elo[row.player_1]
        rating2 = current_elo[row.player_2]
        q1 = pow(10, rating1/DENOM)
        q2 = pow(10, rating2/DENOM)
        expected1 = q1/(q1 + q2)
        expected2 = q2/(q1 + q2)
        gamesPlayed = 1
        wins1 = row.win
        wins2 = 1 - row.win
        played1 = play_counts[row.player_1]
        played2 = play_counts[row.player_2]
        k1 = HIGH_K if played1 < K_CUTOFF else LOW_K
        k2 = HIGH_K if played2 < K_CUTOFF else LOW_K
        newRating1 = rating1 + k1*(wins1 - expected1 * gamesPlayed)
        newRating2 = rating2 + k2*(wins2 - expected2 * gamesPlayed)

        elo_records.append({
            'elo_before_1': rating1,
            'elo_before_2': rating2,
            'games_played_1': play_counts[row.player_1],
            'games_played_2': play_counts[row.player_2],
        })

        play_counts[row.player_1] += 1
        play_counts[row.player_2] += 1

        current_elo[row.player_1] = newRating1
        current_elo[row.player_2] = newRating2


    return historical_records.join(pandas.DataFrame.from_records(elo_records))

def display_elo_checks(games):
    enough_data = games[(games.games_played_1 > K_CUTOFF) & (games.games_played_2 > K_CUTOFF)]
    enough_data['points_diff'] = (enough_data.elo_before_1 - enough_data.elo_before_2).abs()
    enough_data['expected_win'] = (enough_data.elo_before_1 > enough_data.elo_before_2) == enough_data.win

    enough_data['points_bin'] = (enough_data.points_diff / 50).round()*50

    print("Elo Check")
    binned = enough_data.groupby('points_bin').expected_win.agg(['sum', 'count']).reset_index()
    binned['expected_win_rate'] = 1/(1 + (-binned.points_bin/1135.77).rpow(10))
    binned['actual_win_rate'] = binned['sum'] / binned['count']
    display(binned)

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
        display(games)
        games.to_parquet(f"{game_dir}/{name}.parquet", compression="gzip")

    display_elo_checks(games)
    display(games[games.isna().any(axis=1)])
    return os.path.join("bacon", name), games.dropna()
