<script context="module" lang="ts">
    import type {
        AggregatePlayerSkill,
        CharacterPlayCounts,
        EloScales,
        GlickoPlayerSkill,
        GlickoScales,
        MUStats,
        MatchupData,
        PlayerSkill,
        Scales,
    } from "../types";

    const increment = 0.025;
    let xs: number[] = [];
    for (let x = 0; x <= 1; x += increment) {
        xs.push(x);
    }

    function logOdds(winChance: number): number {
        return Math.log(winChance / (1 - winChance));
    }

    function invLogOdds(odds: number): number {
        return Math.exp(odds) / (Math.exp(odds) + 1);
    }

    function formatMU(
        winChance: number,
        func: (p: number) => number = Math.round
    ): string {
        return func(winChance * 40) / 4 + "-" + (10 - func(winChance * 40) / 4);
    }

    type MatchupEstimates = {
        p: number;
        credLower: number;
        credUpper: number;
    }[];
    function vegaSpec(
        muEstimates: MatchupEstimates,
        characters: string[],
        player?: string,
        pSkill?: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ): any {
        const minCredLower = Math.min(
            ...muEstimates
                .filter(function (mu) {
                    return mu.p > 0;
                })
                .map(function (mu) {
                    return mu.credLower;
                })
        );
        const maxCredUpper = Math.max(
            ...muEstimates
                .filter(function (mu) {
                    return mu.p > 0;
                })
                .map(function (mu) {
                    return mu.credUpper;
                })
        );

        const eps = 0.00001;
        const credIntervalExtreme = Math.max(
            Math.abs(0.5 - minCredLower),
            Math.abs(0.5 - maxCredUpper)
        );
        const credIntervalDomain = xs
            .filter(function (x) {
                return (
                    x + eps >=
                        Math.floor((0.5 - credIntervalExtreme) * 20 - 1) / 20 &&
                    x - eps <=
                        Math.ceil((0.5 + credIntervalExtreme) * 20 + 1) / 20
                );
            })
            .map(function (x) {
                return formatMU(x);
            });
        const muEstimate = {
            title: "Matchup Estimate",
            field: "mu",
            type: "ordinal",
            axis: {
                labels: true,
                title: null,
                values: ["3-7", "5-5", "7-3"],
                grid: true,
                gridOpacity: 0.5,
            },
            scale: {
                domain: credIntervalDomain,
            },
        };
        const muLikelihood = {
            title: "Likelihood of Matchup Estimate",
            field: "p",
            type: "quantitative",
            axis: { labels: false, title: null },
            format: ".0%",
            stack: null,
        };

        const overallWinChance = Object.assign(
            {},
            {
                title: "Aggregate Win Estimate",
                field: "cum_p",
                type: "quantitative",
                scale: {
                    scheme: {
                        name: ["#22F", "#DAD", "#F22"],
                        count: 9,
                    },
                    domain: [0.3, 0.7],
                    clamp: true,
                },
                format: ".0%",
                legend: {
                    format: ".0%",
                },
            },
            player
                ? {
                      condition: {
                          test: "datum['type'] == 'global'",
                          value: "transparent",
                      },
                  }
                : {}
        );
        const muNumber = {
            title: "Matchup Value",
            field: "muNumber",
        };
        const statsType = { field: "type", type: "nominal" };
        const muCount = {
            field: "count",
            type: "quantitative",
            title: "MU Games Recorded",
        };
        const pCount = {
            field: "pCount",
            type: "quantitative",
            title: "Player-Character Games Recorded",
            condition: { test: "datum['pCount'] !== null" },
        };
        const oCount = {
            field: "oCount",
            type: "quantitative",
            title: "Opponent-Character Games Recorded",
            condition: { test: "datum['oCount'] !== null" },
        };
        const credInterval = {
            field: "credInterval",
            type: "ordinal",
            title: "90% Chance MU Within",
        };

        const stroke = player
            ? {
                  condition: {
                      test: "datum['type'] == 'global'",
                      value: "#000",
                  },
                  value: "transparent",
              }
            : {
                  value: "transparent",
              };

        const pdf = {
            field: "pdf",
            type: "quantitative",
            stack: null,
            axis: {
                labels: false,
                title: null,
                tickCount: 2,
                gridOpacity: 0.5,
            },
            // scale: {
            //   domain: [
            //     0,
            //     Math.max(
            //       muEstimates.map(function(datum) {
            //         return datum.pdf;
            //       })
            //     )
            //   ]
            // }
        };

        const mark = {
            type: "area",
            stroke: "#000",
            interpolate: "monotone",
        };

        const baseEncoding = {
            x: muEstimate,
            y: pdf,
            detail: statsType,
            tooltip: [
                {
                    field: "mu_name",
                    type: "nominal",
                    title: "Matchup",
                },
                statsType,
                credInterval,
                overallWinChance,
                {
                    field: "muLikelihood",
                    type: "nominal",
                    title: "Estimate",
                },
                muCount,
            ],
            fill: overallWinChance,
            stroke,
        };

        const credIntervalTransform = {
            calculate:
                "join([" +
                "floor(datum.credLower * 20) / 2," +
                "'-'," +
                "(10 - floor(datum.credLower * 20) / 2)," +
                "' - '," +
                "ceil(datum.credUpper * 20) / 2," +
                "'-'," +
                "(10 - ceil(datum.credUpper * 20) / 2)" +
                "], '')",
            as: "credInterval",
        };

        const muLikelihoodTransform = {
            calculate:
                "join([" +
                "format(datum.p, '.0%')," +
                "'chance the MU is'," +
                "datum.mu" +
                "], ' ')",
            as: "muLikelihood",
        };

        const muNumberVal = {
            calculate: "format(datum.cum_p * 10, '.2')",
            // "join([" +
            // "format(datum.cum_p * 10, '.2')," +
            // "' ['," +
            // "format(floor(datum.credLower * 100)/10, '.2')," +
            // "' - '," +
            // "format(ceil(datum.credUpper * 100)/10, '.2')," +
            // "']'," +
            // "], '')",
            as: "muNumber",
        };

        const c1c2Transforms = [
            {
                calculate: "datum.p * datum.winChance",
                as: "w_p",
            },
            {
                joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" },
                ],
                groupby: ["c1", "c2", "type", "v1v2"],
            },
            {
                calculate: "abs(datum.signed_cum_p)",
                as: "cum_p",
            },
            {
                calculate: "join([datum.c1, '/', datum.c2], '')",
                as: "mu_name",
            },
            credIntervalTransform,
            muLikelihoodTransform,
            muNumberVal,
        ];

        const c1Transforms = [
            {
                aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "sum", field: "count", as: "count" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" },
                    { op: "mean", field: "pCount", as: "pCount" },
                ],
                groupby: ["c1", "mu", "type", "v1"],
            },
            {
                calculate: "datum.sum_p / " + (characters.length - 1),
                as: "p",
            },
            {
                calculate: "datum.sum_pdf / " + (characters.length - 1),
                as: "pdf",
            },
            {
                calculate: "datum.p * datum.mean_win_chance",
                as: "w_p",
            },
            {
                joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" },
                ],
                groupby: ["c1", "type"],
            },
            {
                calculate: "abs(datum.signed_cum_p)",
                as: "cum_p",
            },
            credIntervalTransform,
            muLikelihoodTransform,
            muNumberVal,
        ];

        const c2Transforms = [
            {
                aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "sum", field: "count", as: "count" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" },
                    { op: "mean", field: "oCount", as: "oCount" },
                ],
                groupby: ["c2", "mu", "type", "v2"],
            },
            {
                calculate: "datum.sum_p / " + (characters.length - 1),
                as: "p",
            },
            {
                calculate: "datum.sum_pdf / " + (characters.length - 1),
                as: "pdf",
            },
            {
                calculate: "datum.p * datum.mean_win_chance",
                as: "w_p",
            },
            {
                joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" },
                ],
                groupby: ["c2", "type"],
            },
            {
                calculate: "abs(datum.signed_cum_p)",
                as: "cum_p",
            },
            credIntervalTransform,
            muLikelihoodTransform,
            muNumberVal,
        ];

        const allTransforms = [
            {
                aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" },
                ],
                groupby: ["mu", "type"],
            },
            {
                calculate:
                    "datum.sum_p / " +
                    (characters.length - 1) * characters.length,
                as: "p",
            },
            {
                calculate:
                    "datum.sum_pdf / " +
                    (characters.length - 1) * characters.length,
                as: "pdf",
            },
            {
                calculate: "datum.p * datum.mean_win_chance",
                as: "w_p",
            },
            {
                joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" },
                ],
                groupby: ["type"],
            },
            {
                calculate: "abs(datum.signed_cum_p)",
                as: "cum_p",
            },
            credIntervalTransform,
            muLikelihoodTransform,
            muNumberVal,
        ];

        const c1c2Graphs = {
            transform: c1c2Transforms,
            facet: {
                row: {
                    field: "c1",
                    type: "nominal",
                    header: {
                        title: player ? player + " playing " : "Playing",
                        labelAngle: 0,
                        labelAlign: "top",
                    },
                    sort: characters,
                },
                column: {
                    field: "c2",
                    type: "nominal",
                    header: {
                        title: opponent
                            ? "Against " + opponent + " as"
                            : "Against",
                    },
                    sort: characters,
                },
            },
            spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: baseEncoding,
            },
        };

        const c1Graphs = {
            transform: c1Transforms,
            facet: {
                row: {
                    field: "c1",
                    type: "ordinal",
                    header: { title: null, labelAngle: 0, labelAlign: "top" },
                    sort: characters,
                },
            },
            spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: Object.assign({}, baseEncoding, {
                    color: { field: "v1", type: "ordinal" },
                    tooltip: [
                        statsType,
                        credInterval,
                        overallWinChance,
                        {
                            field: "muLikelihood",
                            type: "nominal",
                            title: "Estimate",
                        },
                        muCount,
                        pCount,
                    ],
                }),
            },
        };

        const c2Graphs = {
            transform: c2Transforms,
            facet: {
                column: {
                    field: "c2",
                    type: "ordinal",
                    header: { title: null },
                    sort: characters,
                },
            },
            spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: Object.assign({}, baseEncoding, {
                    color: { field: "v2", type: "ordinal" },
                    tooltip: [
                        statsType,
                        credInterval,
                        overallWinChance,
                        {
                            field: "muLikelihood",
                            type: "nominal",
                            title: "Estimate",
                        },
                        muCount,
                        oCount,
                    ],
                }),
            },
        };

        const allGraphs = {
            transform: allTransforms,
            width: 50,
            height: 40,
            mark: mark,
            encoding: {
                text: muNumber,
                tooltip: [
                    statsType,
                    credInterval,
                    overallWinChance,
                    {
                        field: "muLikelihood",
                        type: "nominal",
                        title: "Estimate",
                    },
                    muCount,
                    pCount,
                ],
            },
        };

        const vlMUs = {
            $schema: "https://vega.github.io/schema/vega-lite/v5.json",
            data: {
                values: muEstimates,
            },
            config: {
                facet: {
                    spacing: {
                        row: 0,
                        column: 0,
                    },
                },
            },
            transform: [
                {
                    // filter: "datum.count > 0 && datum.p >= 0.001"
                },
            ],
            vconcat: [
                {
                    hconcat: [c1c2Graphs, c1Graphs],
                },
                {
                    hconcat: [c2Graphs, allGraphs],
                },
            ],
        };
        return vlMUs;
    }

    function getPlayerSkillDistGlicko(
        scales: GlickoScales,
        againstRating: "self" | number,
        againstCharRating: "self" | number,
        aggregateSkill: AggregatePlayerSkill,
        c1: string,
        c2: string,
        player: string,
        pSkill: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ): gaussian {
        if (!("glicko" in aggregateSkill.globalSkill)) {
            throw Error("No glicko ratings in aggregateSkill");
        }
        if (!("glickoR" in pSkill)) {
            throw Error("No glicko ratings in pSkill");
        }
        if (oSkill && !("glickoR" in oSkill)) {
            throw Error("No glicko ratings in oSkill");
        }

        let oppSkill: GlickoPlayerSkill;
        if (oSkill) {
            oppSkill = oSkill;
        } else {
            if (againstRating === "self") {
                oppSkill = pSkill;
            } else {
                oppSkill = {
                    glickoR:
                        aggregateSkill.globalSkill.glicko.r.qs[againstRating],
                    glickoRD:
                        aggregateSkill.globalSkill.glicko.rd.qs[againstRating],
                    glickoV:
                        aggregateSkill.globalSkill.glicko.v.qs[againstRating],
                    gamesPlayed: -1, // TODO: Add games played quantiles to rendering
                    char: Object.fromEntries(
                        Object.entries(aggregateSkill.characters).map(
                            ([char, skill]) => [
                                char,
                                {
                                    glickoR: skill.glicko.r.qs[againstRating],
                                    glickoRD: skill.glicko.rd.qs[againstRating],
                                    glickoV: skill.glicko.v.qs[againstRating],
                                    gamesPlayed: -1, // TODO: Add games played quantiles to rendering
                                },
                            ]
                        )
                    ),
                };
            }
        }

        const scale = 173.7178;

        function rating_to_mu(rating: number) {
            return (rating - 1500) / scale;
        }

        function rd_to_phi(rd: number) {
            return rd / scale;
        }

        const glickoRDiffDist = gaussian(
            rating_to_mu(pSkill.glickoR),
            Math.pow(rd_to_phi(pSkill.glickoRD), 2)
        ).sub(
            gaussian(
                rating_to_mu(oppSkill.glickoR),
                Math.pow(rd_to_phi(oppSkill.glickoRD), 2)
            )
        );
        const pcGlickoRDiffDist = gaussian(
            rating_to_mu(pSkill.char[c1].glickoR),
            Math.pow(rd_to_phi(pSkill.char[c1].glickoRD), 2)
        ).sub(
            gaussian(
                rating_to_mu(oppSkill.char[c2].glickoR),
                Math.pow(rd_to_phi(oppSkill.char[c2].glickoRD), 2)
            )
        );
        const aggregateSkillDist = glickoRDiffDist.mul(
            scales.glickoScaleMean || 1 - (scales.playerGlobalScaleMean || 0)
        );
        const charSkillDist = pcGlickoRDiffDist.mul(
            scales.pcGlickoScaleMean || scales.playerGlobalScaleMean
        );
        const totalSkillDist = aggregateSkillDist.add(charSkillDist);

        return totalSkillDist;
    }

    function getPlayerSkillDistElo(
        scales: EloScales,
        againstRating: "self" | number,
        againstCharRating: "self" | number,
        aggregateSkill: AggregatePlayerSkill,
        c1: string,
        c2: string,
        player: string,
        pSkill: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ): gaussian {
        if (!("elo" in aggregateSkill)) {
            throw Error("No elo ratings in aggregateSkill");
        }
        if (!("elo" in pSkill)) {
            throw Error("No elo ratings in pSkill");
        }
        if (oSkill && !("elo" in oSkill)) {
            throw Error("No elo ratings in oSkill");
        }
        const eloScaleDist = gaussian(
            scales.eloScaleMean,
            scales.eloScaleStd * scales.eloScaleStd
        );
        const charEloScaleDist = gaussian(
            scales.pcEloScaleMean,
            scales.pcEloScaleStd * scales.pcEloScaleStd
        );

        let oppSkill;
        if (oSkill) {
            oppSkill = oSkill;
        } else {
            if (againstRating === "self") {
                oppSkill = pSkill;
            } else {
                oppSkill = {
                    elo: aggregateSkill.globalSkill.elo.qs[againstRating],
                    char: Object.fromEntries(
                        Object.entries(aggregateSkill.characters).map(
                            ([char, skill]) => [
                                char,
                                { elo: skill.elo.qs[againstRating as number] },
                            ]
                        )
                    ),
                };
            }
        }

        const eloDiff = pSkill.elo - oppSkill.elo;
        const pcEloDiff = pSkill.char[c1].elo - oppSkill.char[c2].elo;

        const eloPctPlayerWin =
            1 / (1 + Math.pow(10, -eloDiff / scales.eloFactor));
        const eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));
        const pcEloPctPlayerWin =
            1 / (1 + Math.pow(10, -pcEloDiff / scales.pcEloFactor));
        const pcEloLogit = Math.log(
            pcEloPctPlayerWin / (1 - pcEloPctPlayerWin)
        );
        if (eloLogit === 0 && pcEloLogit === 0) {
            return null;
        } else if (eloLogit === 0) {
            return charEloScaleDist.scale(pcEloLogit);
        } else if (pcEloLogit === 0) {
            return eloScaleDist.scale(eloLogit);
        } else {
            const eloDist = eloScaleDist.scale(eloLogit);
            const pcEloDist = charEloScaleDist.scale(pcEloLogit);

            const skillDiffDist = eloDist.add(pcEloDist);
            return skillDiffDist;
        }
    }

    function getPlayerSkillDist(
        scales: Scales,
        againstRating: "self" | number,
        againstCharRating: "self" | number,
        aggregateSkill: AggregatePlayerSkill,
        c1: string,
        c2: string,
        player: string,
        pSkill: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ) {
        if ("eloScaleMean" in scales) {
            return getPlayerSkillDistElo(
                scales,
                againstRating,
                againstCharRating,
                aggregateSkill,
                c1,
                c2,
                player,
                pSkill,
                opponent,
                oSkill
            );
        } else {
            return getPlayerSkillDistGlicko(
                scales,
                againstRating,
                againstCharRating,
                aggregateSkill,
                c1,
                c2,
                player,
                pSkill,
                opponent,
                oSkill
            );
        }
    }

    function computeData(
        c1: string,
        c2: string,
        muData: MUStats,
        xs: number[],
        player?: string,
        pSkill?: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill,
        playerDist?: gaussian
    ) {
        const muDist = gaussian(muData.mean, muData.std * muData.std);

        let dist: gaussian;
        if (playerDist && c1 != c2) {
            dist = playerDist.add(muDist);
        } else if (c1 != c2) {
            dist = muDist;
        } else if (playerDist) {
            dist = playerDist;
        }

        const credLower = dist ? invLogOdds(dist.ppf(0.05)) : 0;
        const credUpper = dist ? invLogOdds(dist.ppf(0.95)) : 1;

        let pCount: number;
        let oCount: number;
        if (pSkill) {
            pCount = pSkill.char[c1].gamesPlayed;
            if (oSkill) {
                oCount = oSkill.char[c2].gamesPlayed;
            }
        }
        return xs.map((winChance) => {
            const upper = dist
                ? dist.cdf(logOdds(Math.min(winChance + increment / 2, 1)))
                : 0;
            const lower = dist
                ? dist.cdf(logOdds(Math.max(winChance - increment / 2, 0)))
                : 0;
            return {
                c1,
                c2,
                mu: formatMU(winChance),
                winChance,
                credLower,
                credUpper,
                pdf: dist ? dist.pdf(logOdds(winChance)) : 0,
                p: upper - lower,
                type: player ? "match" : "global",
                count: muData.count,
                pCount,
                oCount,
                player,
                opponent,
            };
        });
    }

    function muPDF(
        scales: Scales,
        againstRating: "self" | number,
        againstCharRating: "self" | number,
        aggregateSkill: AggregatePlayerSkill,
        matchupData: MatchupData,
        c1: string,
        c2: string,
        player?: string,
        pSkill?: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ) {
        const mu = matchupData[c1][c2] || {};

        let playerDist: gaussian;
        if (pSkill && player) {
            playerDist = getPlayerSkillDist(
                scales,
                againstRating,
                againstCharRating,
                aggregateSkill,
                c1,
                c2,
                player,
                pSkill,
                opponent,
                oSkill
            );
        }
        return computeData(
            c1,
            c2,
            mu,
            xs,
            player,
            pSkill,
            opponent,
            oSkill,
            playerDist
        );
    }

    async function renderMUs(
        scales: Scales,
        againstRating: "self" | number,
        againstCharRating: "self" | number,
        aggregateSkill: AggregatePlayerSkill,
        matchupData: MatchupData,
        vis: HTMLElement,
        characters: CharacterPlayCounts,
        game: string,
        player?: string,
        opponent?: string
    ) {
        const playedCharacters = characters
            .filter((char) => char.gamesRecorded > 0)
            .map((char) => char.character);
        console.log({ characters, playedCharacters });
        const pSkill =
            player &&
            (await import(`../data/${game}/player/${player}/skill.json`));
        const oSkill =
            opponent &&
            (await import(`../data/${game}/player/${opponent}/skill.json`));
        const muEstimates = playedCharacters.flatMap(function (c1) {
            return playedCharacters.flatMap(function (c2) {
                let pdf: ReturnType<typeof muPDF> = [];
                pdf = pdf.concat(
                    muPDF(
                        scales,
                        againstRating,
                        againstCharRating,
                        aggregateSkill,
                        matchupData,
                        c1,
                        c2
                    )
                );
                if (player) {
                    pdf = pdf.concat(
                        muPDF(
                            scales,
                            againstRating,
                            againstCharRating,
                            aggregateSkill,
                            matchupData,
                            c1,
                            c2,
                            player,
                            pSkill,
                            opponent,
                            oSkill
                        )
                    );
                }
                return pdf;
            });
        });
        const vlMUs = vegaSpec(
            muEstimates,
            playedCharacters,
            player,
            pSkill,
            opponent,
            oSkill
        );
        await embed(vis, vlMUs);
    }
</script>

<script lang="ts">
    import { onMount } from "svelte";

    import gaussian from "gaussian";

    let vis: HTMLElement;
    import embed from "vega-embed";
    export let characters: CharacterPlayCounts;
    export let matchupData: MatchupData;
    export let scales: Scales;
    export let player: string | undefined;
    export let opponent: string | undefined;
    export let againstRating: "self" | number;
    export let againstCharRating: "self" | number;
    export let aggregateSkill: AggregatePlayerSkill;
    export let game: string;
    const hasVersions = false;

    $: mounted &&
        renderMUs(
            scales,
            againstRating,
            againstCharRating,
            aggregateSkill,
            matchupData,
            vis,
            characters,
            game,
            player,
            opponent
        );
    let mounted = false;
    onMount(() => {
        mounted = true;
    });
</script>

<div id="vis" bind:this={vis} />
