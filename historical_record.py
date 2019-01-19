import pandas
import re
from character import Character, character_category
import numpy as np

HISTORICAL_GSHEET = 'https://docs.google.com/spreadsheets/d/1HcdISgCl3s4RpWkJa8m-G1JjfKzd8qf2WY2Xcw32D7U/pub?gid=1371955398&single=true&output=csv'

def fetch_historical_record(url=HISTORICAL_GSHEET):
    historical_record = pandas.read_csv(url)
    historical_record.columns = [re.sub('\W+', '_', col.lower()).strip('_') for col in historical_record.columns]

    historical_record = historical_record[
        ~historical_record.character_1.isin(['Squall', 'Kefka', 'Ultimicia']) &
        ~historical_record.character_2.isin(['Squall', 'Kefka', 'Ultimicia'])
    ]

    historical_record.character_2.replace(to_replace=['variable'], value=['Gloria'], inplace=True)

    names = pandas.DataFrame({'name': historical_record.player_1.append(historical_record.player_2)})
    names['lower'] = names.apply(lambda r: r['name'].lower(), axis=1)
    name_map = names.groupby('lower').first()

    historical_record['match_date'] = pandas.to_datetime(historical_record.match_date, infer_datetime_format=True)
    historical_record.format_restricted.replace(to_replace=['.', 'Restricted'], value=[False, True], inplace=True)
    historical_record.format_team.replace(to_replace=['.', 'Team'], value=[False, True], inplace=True)
    historical_record.char_select_random.replace(to_replace=['.', 'Random'], value=[False, True], inplace=True)
    historical_record.char_select_locked.replace(to_replace=['.', 'Locked'], value=[False, True], inplace=True)
    historical_record.set_length_non_ft3_ft4.replace(to_replace=['.', 'non-FT3/FT4'], value=[False, True], inplace=True)
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
    return games
