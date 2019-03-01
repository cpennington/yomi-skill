import pandas
import re
from character import Character, character_category
import numpy as np
import os
from datetime import datetime
import logging


HISTORICAL_GSHEET = 'https://docs.google.com/spreadsheets/u/1/d/1HcdISgCl3s4RpWkJa8m-G1JjfKzd8qf2WY2Xcw32D7U/export?format=csv&id=1HcdISgCl3s4RpWkJa8m-G1JjfKzd8qf2WY2Xcw32D7U&gid=1371955398'
ELO_GSHEET = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR5wMDB9AXwmC8N1UEcbbkNNbCcUdnhOmsFRyrXCU8huErk20zKeULEVdAidCijMUc678oOC1F7tgUI/pub?gid=1688184901&single=true&output=csv'

def fetch_name_map(url=HISTORICAL_GSHEET):
    historical_record = pandas.read_csv(url)
    historical_record.columns = [re.sub('\W+', '_', col.lower()).strip('_') for col in historical_record.columns]

    historical_record = historical_record[
        ~historical_record.character_1.isin(['Squall', 'Kefka', 'Ultimicia']) &
        ~historical_record.character_2.isin(['Squall', 'Kefka', 'Ultimicia'])
    ].dropna(subset=['tournament_name'])

    names = pandas.DataFrame({'name': historical_record.player_1.append(historical_record.player_2)})
    names['lower'] = names.apply(lambda r: r['name'].lower(), axis=1)
    name_map = names.groupby('lower').first()
    return name_map

def fetch_historical_record(url=HISTORICAL_GSHEET):
    historical_record = pandas.read_csv(url)
    historical_record.columns = [re.sub('\W+', '_', col.lower()).strip('_') for col in historical_record.columns]

    historical_record = historical_record[
        ~historical_record.character_1.isin(['Squall', 'Kefka', 'Ultimicia']) &
        ~historical_record.character_2.isin(['Squall', 'Kefka', 'Ultimicia'])
    ].dropna(subset=['tournament_name'])

    names = pandas.DataFrame({'name': historical_record.player_1.append(historical_record.player_2)})
    names['lower'] = names.apply(lambda r: r['name'].lower(), axis=1)
    name_map = names.groupby('lower').first()

    historical_record['match_date'] = pandas.to_datetime(historical_record.match_date, infer_datetime_format=True)
    historical_record.set_win_1 = historical_record.set_win_1.fillna(0)
    historical_record.set_win_2 = historical_record.set_win_2.fillna(0)
    historical_record.wins_1 = historical_record.wins_1.fillna(0)
    historical_record.wins_2 = historical_record.wins_2.fillna(0)
    historical_record.character_1 = historical_record.character_1.apply(lambda n: Character(n.lower()))
    historical_record.character_2 = historical_record.character_2.apply(lambda n: Character(n.lower()))
    historical_record.player_1 = historical_record.player_1.apply(lambda n: name_map.loc[n.lower()])
    historical_record.player_2 = historical_record.player_2.apply(lambda n: name_map.loc[n.lower()])

    player_category = pandas.api.types.CategoricalDtype(
        sorted(historical_record.player_1.append(historical_record.player_2).unique()),
        ordered=True
    )

    tournament_category = pandas.api.types.CategoricalDtype(
        sorted(historical_record.tournament_name.unique()),
        ordered=True
    )

    historical_record = historical_record.astype({
        'tournament_name': tournament_category,
        'set_win_1': 'int8',
        'player_1': player_category,
        'character_1': character_category,
        'wins_1': 'int8',
        'wins_2': 'int8',
        'character_2': character_category,
        'player_2': player_category,
        'set_win_2': 'int8',
    })

    return historical_record

def fetch_historical_elo(url=ELO_GSHEET):
    historical_elo = pandas.read_csv(url)
    historical_elo.columns = [re.sub('\W+', '_', col.lower()).strip('_') for col in historical_elo.columns]
    historical_elo = historical_elo[['set_number', 'event', 'match_date', 'elo_1_before', 'set_win_1', 'player_1', 'player_2', 'set_win_2', 'elo_2_before']]
    historical_elo = historical_elo.dropna(subset=['event', 'player_1', 'player_2', 'match_date'])

    name_map = fetch_name_map()

    historical_elo.match_date = pandas.to_datetime(historical_elo.match_date, infer_datetime_format=True)
    historical_elo.set_win_1 = historical_elo.set_win_1.fillna(0)
    historical_elo.set_win_2 = historical_elo.set_win_2.fillna(0)
    historical_elo.player_1 = historical_elo.player_1.apply(lambda n: name_map.loc[n.lower()])
    historical_elo.player_2 = historical_elo.player_2.apply(lambda n: name_map.loc[n.lower()])

    player_category = pandas.api.types.CategoricalDtype(
        sorted(historical_elo.player_1.append(historical_elo.player_2).unique()),
        ordered=True
    )

    tournament_category = pandas.api.types.CategoricalDtype(
        sorted(historical_elo.event.unique()),
        ordered=True
    )
    historical_elo = historical_elo.astype({
        'set_number': int,
        'event': tournament_category,
        'elo_1_before': float,
        # 'elo_1_after': float,
        # 'sets_played_1': int,
        'set_win_1': 'int8',
        'player_1': player_category,
        'player_2': player_category,
        'set_win_2': 'int8',
        'elo_2_before': float,
        # 'elo_2_after': float,
        # 'sets_played_2': int,
        # '5_elo': float,
        # '25_elo': float,
        # '50_elo': float,
        # '75_elo': float,
        # '95_elo': float,
    })

    return historical_elo

def as_player_elo(historical_elo):
    p1_elo = historical_elo[
        ['set_number', 'event', 'match_date', 'elo_1_before', 'player_1']
    ].rename(
        columns={'player_1': 'player', 'elo_1_before': 'elo_before'}
    )
    p2_elo = historical_elo[
        ['set_number', 'event', 'match_date', 'elo_2_before', 'player_2']
    ].rename(
        columns={'player_2': 'player', 'elo_2_before': 'elo_before'}
    )

    all_player_elo = p1_elo.append(p2_elo)
    return all_player_elo.set_index(['set_number', 'player'])

def as_boolean_win_record(historical_record):
    p1_wins = historical_record.loc[np.repeat(historical_record.index.values, historical_record.wins_1.astype(int))].reset_index(drop=True)
    p2_wins = historical_record.loc[np.repeat(historical_record.index.values, historical_record.wins_2.astype(int))].reset_index(drop=True)

    p1_wins['win'] = 1
    p2_wins['win'] = 0

    games = pandas.concat([p1_wins, p2_wins]).reset_index(drop=True)[['tournament_name', 'match_date', 'player_1', 'character_1', 'win', 'character_2', 'player_2']]

    backwards_mus = games.character_1 > games.character_2
    games[backwards_mus] = games[backwards_mus].rename(columns={
        'player_1': 'player_2',
        'player_2': 'player_1',
        'character_1': 'character_2',
        'character_2': 'character_1',
    })
    games.loc[backwards_mus, ['win']] = 1 - games[backwards_mus].win

    mirror_mus_to_flip = list(games[games.character_1 == games.character_2].iloc[::2].index.values)
    games.iloc[mirror_mus_to_flip] = games.iloc[mirror_mus_to_flip].rename(columns={
        'player_1': 'player_2',
        'player_2': 'player_1',
        'character_1': 'character_2',
        'character_2': 'character_1',
    })
    games.iloc[mirror_mus_to_flip, games.columns.get_loc('win')] = 1 - games.iloc[mirror_mus_to_flip].win

    games = games.astype({'win': 'int8'})
    return games.sort_values(['match_date', 'tournament_name'])


def games():
    cached = sorted(os.listdir('games'))
    print("\n".join("{}: {}".format(*choice) for choice in enumerate(cached)))
    pick = input('Load game data:')
    games = None
    if pick:
        picked = cached[int(pick)]
        name, _ = os.path.splitext(picked)
        try:
            games = pandas.read_parquet(f"games/{picked}")
            games.character_1 = games.character_1.apply(lambda n: Character(n.lower()))
            games.character_2 = games.character_2.apply(lambda n: Character(n.lower()))
            games = games.astype({
                'character_1': character_category,
                'character_2': character_category,
            })
        except:
            logging.exception("Can't load %s as parquet", picked)

        if games is None:
            try:
                games = pandas.read_pickle(f"games/{picked}")
            except:
                logging.exception("Can't load %s as pickle", picked)

    if games is None:
        historical_record = fetch_historical_record()
        win_record = as_boolean_win_record(historical_record)
        assert historical_record.wins_1.sum() + historical_record.wins_2.sum() == len(win_record)
        historical_elo = fetch_historical_elo()
        player_elo = as_player_elo(historical_elo)
        assert len(historical_elo) * 2 == len(player_elo)

        mean_elo_by_date = player_elo.groupby(['match_date', 'player']).elo_before.mean()

        games = win_record.join(
            mean_elo_by_date.rename('elo_before_1'), on=['match_date', 'player_1']
        ).join(
            mean_elo_by_date.rename('elo_before_2'), on=['match_date', 'player_2'], rsuffix='_2'
        )
        name = str(datetime.now().isoformat())
        games.astype({
            'character_1': str,
            'character_2': str,
        }).to_parquet(
            f"games/{name}.parquet",
            compression='gzip',
        )

    display(games[games.isna().any(axis=1)])
    return name, games.dropna()