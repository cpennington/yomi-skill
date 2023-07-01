import pandas
import re


def normalize_types(games):

    all_chars = (
        pandas.concat([games.character_1, games.character_2]).rename("character").to_frame()
    )
    all_chars["normalized"] = all_chars.character.apply(lambda v: v.lower())

    char_map = (
        all_chars.groupby("normalized")
        .character.agg(pandas.Series.mode)
        .reset_index()[["normalized", "character"]]
        .set_index("normalized")
        .character
    )

    all_chars["standardized"] = all_chars.normalized.apply(lambda c: char_map[c])
    all_chars = all_chars.drop_duplicates().set_index(["character"])

    games.character_1 = games.character_1.apply(lambda c: all_chars.standardized[c])
    games.character_2 = games.character_2.apply(lambda c: all_chars.standardized[c])

    character_category = pandas.api.types.CategoricalDtype(
        sorted(pandas.concat([games.character_1, games.character_2]).unique()), ordered=True
    )

    all_players = pandas.concat([games.player_1, games.player_2]).rename("player").to_frame()
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
        sorted(pandas.concat([games.player_1, games.player_2]).unique()), ordered=True
    )

    return games.astype(
        {
            "player_1": player_category,
            "character_1": character_category,
            "win": "int8",
            "character_2": character_category,
            "player_2": player_category,
            "elo_before_1": float,
            "elo_before_2": float,
        }
    )
