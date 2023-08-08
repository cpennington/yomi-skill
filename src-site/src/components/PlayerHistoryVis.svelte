<script lang="ts">
    import { getContext, onMount } from "svelte";
    import embed from "vega-embed";

    type AugMatch = Match & {
        index?: number;
        ratingP?: number;
        devP?: number;
        ratingO?: number;
        ratingDelta?: number;
    };

    async function renderPlayerHistory(
        games: string,
        player?: string,
        opponent?: string
    ) {
        const playerMatches =
            player &&
            (await import(`../data/yomi/player/${player}/history.json`))
                .default;

        const opponentMatches =
            opponent &&
            (await import(`../data/yomi/player/${opponent}/history.json`))
                .default;

        if (playerMatches || opponentMatches) {
            const matchDateField = {
                field: "render__match_date",
                type: "temporal",
            };
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
            const playerRatingField = {
                field: "ratingP",
                type: "quantitative",
                title: "Player Rating",
            };
            const opponentRatingField = {
                field: "ratingO",
                type: "quantitative",
                title: "Opponent Rating",
            };

            const yomiRatingTooltips = [
                matchDateField,
                playerField,
                oppField,
                playerRatingField,
                opponentRatingField,
            ];

            function processMatches(matches: AugMatch[]) {
                matches.forEach((match, idx) => {
                    match["index"] = idx;
                    match["ratingP"] = match.elo__rp || match.glicko__rp;
                    match["devP"] = match.glicko__rdp * 2 || 0;
                    match["ratingO"] = match.elo__ro || match.glicko__ro;
                    const nextMatch = matches[idx + 1];
                    if (nextMatch) {
                        match["ratingDelta"] =
                            (nextMatch.elo__rp || nextMatch.glicko__rp) -
                            match.ratingP;
                    }
                });
            }

            processMatches(playerMatches);
            opponentMatches && processMatches(opponentMatches);

            const allMatches = playerMatches.concat(opponentMatches);
            console.log(allMatches);
            const vlMatches = {
                $schema: "https://vega.github.io/schema/vega-lite/v4.json",
                data: {
                    values: allMatches,
                    format: {
                        parse: { render__match_date: "date" },
                    },
                },
                vconcat: [
                    {
                        width: 1500,
                        height: 100,
                        transform:
                            game == "yomi"
                                ? [
                                      //   { filter: "datum.ratingDelta != 0" },
                                      {
                                          aggregate: [
                                              {
                                                  op: "min",
                                                  field: "index",
                                                  as: "index",
                                              },
                                              {
                                                  op: "mean",
                                                  field: "ratingDelta",
                                                  as: "ratingDelta",
                                              },
                                              {
                                                  op: "mean",
                                                  field: "ratingP",
                                                  as: "ratingP",
                                              },
                                              {
                                                  op: "mean",
                                                  field: "ratingO",
                                                  as: "ratingO",
                                              },
                                          ],
                                          groupby: [
                                              "player",
                                              "opponent",
                                              "render__match_date",
                                          ],
                                      },
                                  ]
                                : [],
                        mark: {
                            type: "bar",
                        },
                        encoding: {
                            x: { field: "index", type: "ordinal" },
                            y: { field: "ratingDelta", type: "quantitative" },
                            row: { field: "player", type: "nominal" },
                            color: {
                                condition: [
                                    {
                                        test: "datum.ratingDelta > 0 && datum.ratingP > datum.ratingO",
                                        value: "#050",
                                    },
                                    {
                                        test: "datum.ratingDelta > 0 && datum.ratingP < datum.ratingO",
                                        value: "#0d0",
                                    },
                                    {
                                        test: "datum.ratingDelta < 0 && datum.ratingP < datum.ratingO",
                                        value: "#500",
                                    },
                                ],
                                value: "#d00",
                            },
                            tooltip: yomiRatingTooltips,
                        },
                    },
                    {
                        width: 1500,
                        height: 200,
                        layer: [
                            {
                                mark: {
                                    type: "errorband",
                                },
                                encoding: {
                                    x: {
                                        field: "render__match_date",
                                        type: "temporal",
                                        timeUnit: "yearmonthdate",
                                    },
                                    y: {
                                        field: "ratingP",
                                        type: "quantitative",
                                        scale: { zero: false },
                                    },
                                    yError: {
                                        field: "devP",
                                    },
                                    color: {
                                        field: "player",
                                        type: "nominal",
                                    },
                                },
                            },
                            {
                                mark: {
                                    type: "line",
                                    interpolate: "step-after",
                                    point: "transparent",
                                },
                                encoding: {
                                    x: {
                                        field: "render__match_date",
                                        type: "temporal",
                                        timeUnit: "yearmonthdate",
                                    },
                                    y: {
                                        field: "ratingP",
                                        type: "quantitative",
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
                                    tooltip: yomiRatingTooltips,
                                },
                            },
                        ],
                    },
                ],
            };

            embed("#player-vis", vlMatches);
        }
    }

    export let game: string;
    export let player: string;
    export let opponent: string;

    $: mounted && renderPlayerHistory(game, player, opponent);
    let mounted = false;
    onMount(() => {
        mounted = true;
    });
</script>

<div id="player-vis" />
