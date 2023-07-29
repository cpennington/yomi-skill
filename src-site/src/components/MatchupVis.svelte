<script context="module" lang="ts">
    const increment = 0.05;
    type PlayerSkill = {
        char: Record<string, { elo: number; gamesPlayed: number }>;
        elo: number;
        gamesPlayed: number;
    };
    type AggregatePlayerSkill = {
        char_elo_q: { string: { qs: number[]; std: number } };
        elo: { qs: number[]; std: number };
    };
    type Scales = {
        eloScaleMean: number;
        eloScaleStd: number;
        eloFactor: number;
        pcEloScaleMean: number;
        pcEloScaleStd: number;
        pcEloFactor: number;
    };
    type MUStats = {
        count: number;
        mean: number;
        std: number;
    };
    type MatchupData = Record<string, Record<string, MUStats>>;

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
        return func(winChance * 20) / 2 + "-" + (10 - func(winChance * 20) / 2);
    }

    type MatchupEstimates = {
        p: number;
        credLower: number;
        credUpper: number;
    }[];
    function vegaSpec(
        muEstimates: MatchupEstimates,
        textOnly: boolean,
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
        console.log({ xs, credIntervalExtreme, minCredLower, maxCredUpper });
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

        const mark = textOnly
            ? { type: "text" }
            : {
                  type: "area",
                  stroke: "#000",
                  interpolate: "monotone",
              };

        const baseEncoding = textOnly
            ? {
                  text: muNumber,
              }
            : {
                  x: muEstimate,
                  y: pdf,
                  detail: statsType,
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
                        labelAngle: -45,
                    },
                    sort: characters,
                },
            },
            spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: baseEncoding,
                // Object.assign({}, baseEncoding, {
                //     color: Object.assign(
                //         {},
                //         { field: "newestVersion", type: "ordinal" },
                //         player
                //             ? {
                //                   condition: {
                //                       test: "datum['type'] == 'global'",
                //                       value: "#bbb",
                //                   },
                //               }
                //             : {}
                //     ),
                //     tooltip: hasVersions
                //         ? [
                //               {
                //                   field: "mu_name",
                //                   type: "nominal",
                //                   title: "Matchup",
                //               },
                //               { field: "v1v2", type: "ordinal" },
                //               statsType,
                //               credInterval,
                //               overallWinChance,
                //               {
                //                   field: "muLikelihood",
                //                   type: "nominal",
                //                   title: "Estimate",
                //               },
                //               muCount,
                //               pCount,
                //               oCount,
                //           ]
                //         : [
                //               {
                //                   field: "mu_name",
                //                   type: "nominal",
                //                   title: "Matchup",
                //               },
                //               statsType,
                //               credInterval,
                //               overallWinChance,
                //               {
                //                   field: "muLikelihood",
                //                   type: "nominal",
                //                   title: "Estimate",
                //               },
                //               muCount,
                //               pCount,
                //               oCount,
                //           ],
                // }),
            },
        };
        const c1c2Text = {
            transform: c1c2Transforms,
            width: 700,
            height: 700,
            encoding: {
                y: {
                    field: "c1",
                    type: "nominal",
                    header: {
                        title: player ? player + " playing " : "Playing",
                        labelAngle: 0,
                    },
                    sort: characters,
                },
                x: {
                    field: "c2",
                    type: "nominal",
                    header: {
                        title: opponent
                            ? "Against " + opponent + " as"
                            : "Against",
                        labelAngle: -45,
                    },
                    sort: characters,
                },
            },
            layer: [
                { mark: "rect", encoding: baseEncoding },
                {
                    mark: "text",
                    encoding: {
                        text: muNumber,
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
                            pCount,
                            oCount,
                        ],
                    },
                },
            ],
        };

        const c1Graphs = {
            transform: c1Transforms,
            facet: {
                row: {
                    field: "c1",
                    type: "ordinal",
                    header: { title: null, labelAngle: 0 },
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

        const c1Text = {
            transform: c1Transforms,
            width: 35,
            height: 700,
            encoding: {
                y: {
                    field: "c1",
                    type: "nominal",
                    header: {
                        title: player ? player + " playing " : "Playing",
                        labelAngle: 0,
                    },
                    sort: characters,
                },
            },
            layer: [
                { mark: "rect", encoding: baseEncoding },
                {
                    mark: "text",
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
                },
            ],
        };

        const c2Graphs = {
            transform: c2Transforms,
            facet: {
                column: {
                    field: "c2",
                    type: "ordinal",
                    header: { title: null, labelAngle: -45 },
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

        const c2Text = {
            transform: c2Transforms,
            width: 700,
            height: 35,
            encoding: {
                x: {
                    field: "c2",
                    type: "nominal",
                    header: {
                        title: player ? player + " playing " : "Playing",
                        labelAngle: 0,
                    },
                    sort: characters,
                },
            },
            layer: [
                { mark: "rect", encoding: baseEncoding },
                {
                    mark: "text",
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
                },
            ],
        };

        const allGraphs = {
            transform: allTransforms,
            width: 35,
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

        const allText = {
            transform: allTransforms,
            width: 35,
            height: 35,
            layer: [
                { mark: "rect", encoding: baseEncoding },
                {
                    mark: "text",
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
                },
            ],
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
                    hconcat: [
                        textOnly ? c1c2Text : c1c2Graphs,
                        textOnly ? c1Text : c1Graphs,
                    ],
                },
                {
                    hconcat: [
                        textOnly ? c2Text : c2Graphs,
                        textOnly ? allText : allGraphs,
                    ],
                },
            ],
        };
        return vlMUs;
    }

    function getPlayerSkillDist(
        scales: Scales,
        againstElo: "self" | number,
        playerSkill: AggregatePlayerSkill,
        c1: string,
        c2: string,
        player: string,
        pSkill: PlayerSkill,
        opponent?: string,
        oSkill?: PlayerSkill
    ): gaussian {
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
            if (againstElo === "self") {
                oppSkill = pSkill;
            } else {
                oppSkill = {
                    elo: playerSkill.elo.qs[againstElo],
                    char: Object.fromEntries(
                        Object.entries(playerSkill.char_elo_q).map(
                            ([char, data]) => [
                                char,
                                { elo: data.qs[againstElo as number] },
                            ]
                        )
                    ),
                };
            }
        }

        const eloDiff = pSkill.elo - oppSkill.elo;
        const pcEloDiff = pSkill.char[c1].elo - oppSkill.char[c2].elo;

        // 1135.77 means that 200 points rating difference gets a 60% win rate
        // see http://www.mtgeloproject.net/faq.php
        const eloPctPlayerWin =
            1 / (1 + Math.pow(10, -eloDiff / scales.elo_factor));
        const eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));
        const pcEloPctPlayerWin =
            1 / (1 + Math.pow(10, -pcEloDiff / scales.pc_elo_factor));
        const pcEloLogit = Math.log(
            pcEloPctPlayerWin / (1 - pcEloPctPlayerWin)
        );

        console.log({
            c1,
            c2,
            eloPctPlayerWin,
            pcEloPctPlayerWin,
            eloScaleDist,
            charEloScaleDist,
            eloDiff,
            pcEloDiff,
            eloLogit,
            pcEloLogit,
            scales,
            pSkill,
            oppSkill,
        });
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

            console.log({
                eloDist,
                pcEloDist,
                skillDiffDist,
            });
            return skillDiffDist;
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
        againstElo: "self" | number,
        playerSkill: AggregatePlayerSkill,
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
                againstElo,
                playerSkill,
                c1,
                c2,
                player,
                pSkill,
                opponent,
                oSkill
            );
            console.log({ player, playerDist });
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
        againstElo: "self" | number,
        playerSkill: AggregatePlayerSkill,
        matchupData: MatchupData,
        vis: HTMLElement,
        characters: string[],
        textOnly: boolean,
        player?: string,
        opponent?: string
    ) {
        const pSkill =
            player &&
            (await import(`../data/yomi/player/${player}/skill.json`));
        const oSkill =
            opponent &&
            (await import(`../data/yomi/player/${opponent}/skill.json`));
        console.log({ fn: "renderMUs", pSkill, oSkill });
        const muEstimates = characters.flatMap(function (c1) {
            return characters.flatMap(function (c2) {
                let pdf: ReturnType<typeof muPDF> = [];
                pdf = pdf.concat(
                    muPDF(scales, againstElo, playerSkill, matchupData, c1, c2)
                );
                if (player) {
                    pdf = pdf.concat(
                        muPDF(
                            scales,
                            againstElo,
                            playerSkill,
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
            textOnly,
            characters,
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
    export let characters: string[];
    export let matchupData: MatchupData;
    export let scales: Scales;
    export let textOnly: boolean;
    export let player: string | undefined;
    export let opponent: string | undefined;
    export let againstElo: "self" | number;
    export let playerSkill: AggregatePlayerSkill;
    const hasVersions = false;

    $: mounted &&
        renderMUs(
            scales,
            againstElo,
            playerSkill,
            matchupData,
            vis,
            characters,
            textOnly,
            player,
            opponent
        );
    let mounted = false;
    onMount(() => {
        mounted = true;
        renderMUs(
            scales,
            againstElo,
            playerSkill,
            matchupData,
            vis,
            characters,
            textOnly,
            player,
            opponent
        );
    });
</script>

<div id="vis" bind:this={vis} />
