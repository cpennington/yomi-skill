<script>
    import { getContext } from "svelte";
    import embed from "vega-embed";

    let game;
    let player;
    let opponent;

    let playerMatches;
    $: {
        player &&
            import(`./data/${game}/playerData/${player}.json`).then((data) => {
                playerMatches = data;
            });
    }
    let opponentMatches;
    $: {
        opponent &&
            import(`./data/${game}/playerData/${opponent}.json`).then(
                (data) => {
                    opponentMatches = data;
                }
            );
    }

    if (playerMatches) {
        const matchDateField = { field: "match_date", type: "temporal" };
        const playerField = {
            field: "player",
            type: "nominal",
            title: "Player",
        };
        const charPlayerField = {
            field: "character_p",
            type: "nominal",
            title: "Playing as",
        };
        const oppField = {
            field: "opponent",
            type: "nominal",
            title: "Opponent",
        };
        const charOpponentField = {
            field: "character_o",
            type: "nominal",
            title: "Opponent as",
        };
        const eloPlayerField = {
            field: "elo_before_p",
            type: "quantitative",
            title: "Player Elo",
        };
        const eloOpponentField = {
            field: "elo_before_o",
            type: "quantitative",
            title: "Opponent Elo",
        };
        const eventField = {
            field: "tournament_name",
            type: "nominal",
            title: "Tournament",
        };

        const baconEloTooltips = [
            matchDateField,
            playerField,
            charPlayerField,
            oppField,
            charOpponentField,
            eloPlayerField,
            eloOpponentField,
        ];

        const yomiEloTooltips = [
            matchDateField,
            eventField,
            playerField,
            oppField,
            eloPlayerField,
            eloOpponentField,
        ];

        Array.from(playerMatches).forEach(function (match, idx) {
            match["player"] = player;
            match["index"] = idx;
            if (match.elo_after_p || playerMatches[idx + 1]) {
                match["eloDelta"] =
                    (match.elo_after_p || playerMatches[idx + 1].elo_before_p) -
                    match.elo_before_p;
            }
        });
        Array.from(opponentMatches).forEach(function (match, idx) {
            match["player"] = opponent;
            match["index"] = idx;
            if (match.elo_after_p || opponentMatches[idx + 1]) {
                match["eloDelta"] =
                    (match.elo_after_p ||
                        opponentMatches[idx + 1].elo_before_p) -
                    match.elo_before_p;
            }
        });

        const allMatches = playerMatches.concat(opponentMatches);

        const vlMatches = {
            $schema: "https://vega.github.io/schema/vega-lite/v4.json",
            data: {
                values: allMatches,
                format: {
                    parse: { match_date: "date" },
                },
            },
            vconcat: [
                {
                    width: 1500,
                    height: 100,
                    transform: [{ filter: "datum.eloDelta != 0" }],
                    mark: {
                        type: "bar",
                    },
                    transform:
                        game == "yomi"
                            ? [
                                  {
                                      aggregate: [
                                          {
                                              op: "min",
                                              field: "index",
                                              as: "index",
                                          },
                                          {
                                              op: "mean",
                                              field: "eloDelta",
                                              as: "eloDelta",
                                          },
                                          {
                                              op: "mean",
                                              field: "elo_before_p",
                                              as: "elo_before_p",
                                          },
                                          {
                                              op: "mean",
                                              field: "elo_before_o",
                                              as: "elo_before_o",
                                          },
                                      ],
                                      groupby: [
                                          "player",
                                          "opponent",
                                          "match_date",
                                          "tournament_name",
                                      ],
                                  },
                              ]
                            : [],
                    encoding: {
                        x: { field: "index", type: "ordinal" },
                        y: { field: "eloDelta", type: "quantitative" },
                        row: { field: "player", type: "nominal" },
                        color: {
                            condition: [
                                {
                                    test: "datum.eloDelta > 0 && datum.elo_before_p > datum.elo_before_o",
                                    value: "#050",
                                },
                                {
                                    test: "datum.eloDelta > 0 && datum.elo_before_p < datum.elo_before_o",
                                    value: "#0d0",
                                },
                                {
                                    test: "datum.eloDelta < 0 && datum.elo_before_p < datum.elo_before_o",
                                    value: "#500",
                                },
                            ],
                            value: "#d00",
                        },
                        tooltip:
                            game == "bacon"
                                ? baconEloTooltips
                                : yomiEloTooltips,
                    },
                },
                {
                    width: 1500,
                    height: 200,
                    mark: {
                        type: "line",
                        interpolate: "step-after",
                        point: "transparent",
                    },
                    encoding: {
                        x: {
                            field: "match_date",
                            type: "temporal",
                            timeUnit: "yearmonthdate",
                        },
                        y: {
                            field: "elo_before_p",
                            type: "quantitative",
                            aggregate: "mean",
                            scale: { zero: false },
                        },
                        color: {
                            field: "player",
                            type: "nominal",
                        },
                        detail: {
                            field: "player",
                            type: "nominal",
                        },
                        tooltip:
                            game == "bacon"
                                ? baconEloTooltips
                                : yomiEloTooltips,
                    },
                },
            ],
        };

        embed("#player-vis", vlMatches);
    }
</script>

<div id="player-vis" />
