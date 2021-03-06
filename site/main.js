const staticRoot = document.getElementById("static-root").innerText;
const game = document.getElementById("game-id").innerText;
const matchupDataPromise = fetch(
  encodeURI(staticRoot + "/" + game + "/matchupData.json")
).then(function (response) {
  return response.json();
});
const charactersPromise = fetch(
  encodeURI(staticRoot + "/" + game + "/characters.json")
).then(function (response) {
  return response.json();
});
const playerSkillPromise = fetch(
  encodeURI(staticRoot + "/" + game + "/playerSkill.json")
).then(function (response) {
  return response.json();
});
const eloScalePromise = fetch(
  encodeURI(staticRoot + "/" + game + "/eloScale.json")
).then(function (response) {
  return response.json();
});

Promise.all([
  matchupDataPromise,
  charactersPromise,
  playerSkillPromise,
  eloScalePromise,
]).then(([matchupData, characters, playerSkill, eloScale]) => {
  const eloScaleDist = gaussian(eloScale.mean, eloScale.std * eloScale.std);
  const playerInput = document.getElementById("player");
  const opponentInput = document.getElementById("opponent");
  const playersList = document.getElementById("players");
  const loading = document.getElementById("loading");
  const vis = document.getElementById("vis");
  const againstCfg = document.getElementById("against-cfg");
  const playerStats = document.getElementById("player-stats");
  const p1Stats = document.getElementById("p1-stats");
  const p2Stats = document.getElementById("p2-stats");
  const increment = 0.05;

  var hasVersions = !!matchupData[characters[0]][characters[0]].versions;

  playerInput.onblur = updatePlayerStats;
  opponentInput.onblur = updatePlayerStats;

  const quantiles = [0.05, 0.25, 0.5, 0.75, 0.95, 1];
  const medianPlayerSkill = {};
  const medianPlayerElo = {};
  characters.forEach((char) => {
    medianPlayerSkill[char] = {};
    var skillQValues = math.quantileSeq(
      Object.entries(playerSkill)
        .map(function (skillsByChar) {
          var charStats = skillsByChar[1][char];
          if (charStats) {
            return charStats.mean;
          } else {
            return null;
          }
        })
        .filter(function (v) {
          return v != null;
        }),
      quantiles
    );

    var std = math.mean(
      Object.entries(playerSkill)
        .map(function (skillsByChar) {
          var charStats = skillsByChar[1][char];
          if (charStats) {
            return charStats.std;
          } else {
            return null;
          }
        })
        .filter(function (v) {
          return v != null;
        })
    );

    var eloQValues = math.quantileSeq(
      Object.values(playerSkill)
        .map(function (skill) {
          return skill.elo;
        })
        .filter(function (v) {
          return v >= 0;
        }),
      quantiles
    );

    quantiles.forEach(function (q, idx) {
      medianPlayerSkill[char][q * 100 + "%"] = {
        mean: skillQValues[idx],
        std: std,
      };
      medianPlayerElo[q * 100 + "%"] = eloQValues[idx];
    });
  });

  Object.entries(playerSkill)
    .map(function (entry) {
      return [entry[1].gamesPlayed, entry[0]];
    })
    .sort(function (a, b) {
      return a[0] < b[0];
    })
    .forEach(function (entry) {
      var opt = document.createElement("option");
      opt.value = entry[1];
      opt.textContent = entry[1] + " (" + entry[0] + " games recorded)";
      playersList.appendChild(opt);
    });

  var xs = [];
  for (var x = 0; x <= 1; x += increment) {
    xs.push(x);
  }

  var percPts = [];
  for (var pp = 0; pp <= 1; pp += 0.001) {
    percPts.push(pp);
  }

  function logOdds(winChance) {
    return Math.log(winChance / (1 - winChance));
  }

  function invLogOdds(odds) {
    return Math.exp(odds) / (Math.exp(odds) + 1);
  }

  function formatMU(winChance, func) {
    func = func || Math.round;
    return func(winChance * 20) / 2 + "-" + (10 - func(winChance * 20) / 2);
  }

  function getOSkillDist(player, againstChar) {
    const againstSkillPick = Array.from(
      document.getElementsByName("against-skill")
    )
      .map(function (e) {
        return e.checked ? e.value : null;
      })
      .filter(function (v) {
        return v != null;
      })[0];
    var oSkill;
    if (againstSkillPick === "self") {
      oSkill = {
        mean: math.mean(
          characters.map(function (char) {
            return playerSkill[player][char].mean;
          })
        ),
        std: math.mean(
          characters.map(function (char) {
            return playerSkill[player][char].std;
          })
        ),
      };
    } else {
      oSkill = medianPlayerSkill[againstChar][againstSkillPick];
    }
    return gaussian(oSkill.mean, oSkill.std * oSkill.std);
  }

  function getAgainstEloDiff(player) {
    const againstEloPick = Array.from(document.getElementsByName("against-elo"))
      .map(function (e) {
        return e.checked ? e.value : null;
      })
      .filter(function (v) {
        return v != null;
      })[0];
    if (againstEloPick === "self") {
      return 0;
    } else {
      return playerSkill[player].elo - medianPlayerElo[againstEloPick];
    }
  }

  function getPlayerSkillDist(player, opponent, c1, c2) {
    const pSkill = playerSkill[player][c1];
    const pSkillDist = gaussian(pSkill.mean, pSkill.std * pSkill.std);
    if (opponent) {
      const oSkill = playerSkill[opponent][c2];
      const oSkillDist = gaussian(oSkill.mean, oSkill.std * oSkill.std);

      const eloDiff = playerSkill[player].elo - playerSkill[opponent].elo;
      eloPctPlayerWin = 1 / (1 + Math.pow(10, -eloDiff / 1135.77));
      eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));

      return pSkillDist.sub(oSkillDist).add(eloScaleDist.scale(eloLogit));
    } else {
      const oSkillDist = getOSkillDist(player, c2);
      const eloDiff = getAgainstEloDiff(player);

      // 1135.77 means that 200 points rating difference gets a 60% win rate
      // see http://www.mtgeloproject.net/faq.php
      eloPctPlayerWin = 1 / (1 + Math.pow(10, -eloDiff / 1135.77));
      eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));

      var dist = pSkillDist.sub(oSkillDist);
      if (eloDiff != 0) {
        dist = dist.add(eloScaleDist.scale(eloLogit));
      }
      return dist;
    }
  }

  function computeDatum(c1, c2, muData, x, player, opponent, playerDist) {
    const muDist = gaussian(muData.mean, muData.std * muData.std);

    var dist;
    if (player && c1 != c2) {
      dist = playerDist.add(muDist);
    } else if (c1 != c2) {
      dist = muDist;
    } else if (player) {
      dist = playerDist;
    }

    const upper = dist ? dist.cdf(logOdds(Math.min(x + increment / 2, 1))) : 0;
    const lower = dist ? dist.cdf(logOdds(Math.max(x - increment / 2, 0))) : 0;

    var datum = {
      c1: c1,
      c2: c2,
      mu: formatMU(x),
      winChance: x,
      credLower: dist ? invLogOdds(dist.ppf(0.05)) : 0,
      credUpper: dist ? invLogOdds(dist.ppf(0.95)) : 1,
      pdf: dist ? dist.pdf(logOdds(x)) : 0,
      p: upper - lower,
      type: player ? "match" : "global",
      count: muData.counts,
    };
    if (player) {
      datum.pCount = playerSkill[player][c1].played;
      if (opponent) {
        datum.oCount = playerSkill[opponent][c2].played;
      }
      datum.player = player;
    }
    if (opponent) {
      datum.opponent = opponent;
    }
    return datum;
  }

  function muPDF(c1, c2, player, opponent) {
    const mu = matchupData[c1][c2] || {};
    const versions = mu.versions;

    var data = xs.flatMap(function (x) {
      var playerDist;
      if (player) {
        playerDist = getPlayerSkillDist(player, opponent, c1, c2);
      }
      var data2;
      if (versions !== undefined) {
        data2 = Object.entries(versions).flatMap(function (versions) {
          const v1 = versions[0];
          return Object.entries(versions[1]).flatMap(function (version) {
            const v2 = version[0];
            return Object.assign(
              computeDatum(c1, c2, version[1], x, player, opponent, playerDist),
              {
                v1: v1,
                v2: v2,
                v1v2: v1 + "/" + v2,
                newestVersion: Math.max(v1, v2),
              }
            );
          });
        });
        if (data2.length == 0) {
          data2 = [
            {
              c1: c1,
              c2: c2,
              v1: "N/A",
              v2: "N/A",
              v1v2: "N/A",
              newestVersion: "N/A",
              mu: formatMU(x),
              winChance: x,
              credLower: 0,
              credUpper: 1,
              pdf: 0,
              p: 0,
              type: player ? "match" : "global",
              count: 0,
            },
          ];
        }
      } else {
        data2 = computeDatum(c1, c2, mu, x, player, opponent, playerDist);
      }

      return data2;
    });
    return data;
  }

  function updatePlayerStats() {
    const player = playerSkill[playerInput.value] && playerInput.value;
    const opponent = playerSkill[opponentInput.value] && opponentInput.value;

    playerStats.style.display = player || opponent ? "table" : "none";
    againstCfg.style.display = player && !opponent ? "block" : "none";
    p1Stats.style.display = player ? "table-row" : "none";
    p2Stats.style.display = opponent ? "table-row" : "none";

    if (player) {
      document.getElementById("p1-name").textContent = player;
      document.getElementById("p1-elo").textContent = Math.round(
        playerSkill[player].elo
      );
      document.getElementById("p1-games").textContent =
        playerSkill[player].gamesPlayed;
    }
    if (opponent) {
      againstCfg.display = "none";
      document.getElementById("p2-name").textContent = opponent;
      document.getElementById("p2-elo").textContent = Math.round(
        playerSkill[opponent].elo
      );
      document.getElementById("p2-games").textContent =
        playerSkill[opponent].gamesPlayed;
    }
  }

  function exportCSV(player, opponent) {
    muPDFs = characters.flatMap(function (c1) {
      return characters.flatMap(function (c2) {
        return muPDF(c1, c2, player, opponent);
      });
    });

    var muEstimates = Object.fromEntries(
      characters.map((c1) => [
        c1,
        Object.fromEntries(characters.map((c2) => [c2, 0])),
      ])
    );
    muPDFs.forEach(
      (pdfSegment) =>
        (muEstimates[pdfSegment.c1][pdfSegment.c2] +=
          pdfSegment.winChance * pdfSegment.p)
    );
    if (!player && !opponent) {
      characters.forEach((c) => (muEstimates[c][c] = 0.5));
    }
    var csvContent = "data:text/csv;charset=utf-8,";

    csvContent += [["MU Estimates"].concat(characters).join(", ")]
      .concat(
        characters.map((c1) =>
          [c1]
            .concat(characters.map((c2) => muEstimates[c1][c2].toString()))
            .join(", ")
        )
      )
      .join("\n");
    window.open(encodeURI(csvContent));
  }

  function comparePlayers(player, opponent, textOnly) {
    loading.style.display = "inline";

    setTimeout(function () {
      muEstimates = characters.flatMap(function (c1) {
        return characters.flatMap(function (c2) {
          var pdf = [];
          pdf = pdf.concat(muPDF(c1, c2));
          if (player) {
            pdf = pdf.concat(muPDF(c1, c2, player, opponent));
          }
          return pdf;
        });
      });

      const minCredLower = math.min(
        muEstimates
          .filter(function (mu) {
            return mu.p > 0;
          })
          .map(function (mu) {
            return mu.credLower;
          })
      );
      const maxCredUpper = math.max(
        muEstimates
          .filter(function (mu) {
            return mu.p > 0;
          })
          .map(function (mu) {
            return mu.credUpper;
          })
      );

      const eps = 0.00001;
      const credIntervalExtreme = math.max(
        math.abs(0.5 - minCredLower),
        math.abs(0.5 - maxCredUpper)
      );
      const credIntervalDomain = xs
        .filter(function (x) {
          return (
            x + eps >= math.floor((0.5 - credIntervalExtreme) * 20 - 1) / 20 &&
            x - eps <= math.ceil((0.5 + credIntervalExtreme) * 20 + 1) / 20
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
        axis: { labels: false, title: null, tickCount: 2, gridOpacity: 0.5 },
        // scale: {
        //   domain: [
        //     0,
        //     math.max(
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
            type: hasVersions ? "line" : "area",
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
              { field: "muLikelihood", type: "nominal", title: "Estimate" },
              muCount,
            ],
          };
      if (!hasVersions) {
        baseEncoding["fill"] = overallWinChance;
        baseEncoding["stroke"] = stroke;
      }

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
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
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
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
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
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
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
            "datum.sum_p / " + (characters.length - 1) * characters.length,
          as: "p",
        },
        {
          calculate:
            "datum.sum_pdf / " + (characters.length - 1) * characters.length,
          as: "pdf",
        },
        {
          calculate: "datum.p * datum.mean_win_chance",
          as: "w_p",
        },
        {
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
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
              title: opponent ? "Against " + opponent + " as" : "Against",
              labelAngle: -45,
            },
            sort: characters,
          },
        },
        spec: {
          width: 50,
          height: 40,
          mark: mark,
          encoding: Object.assign({}, baseEncoding, {
            color: Object.assign(
              {},
              { field: "newestVersion", type: "ordinal" },
              player
                ? {
                    condition: {
                      test: "datum['type'] == 'global'",
                      value: "#bbb",
                    },
                  }
                : {}
            ),
            tooltip: hasVersions
              ? [
                  { field: "mu_name", type: "nominal", title: "Matchup" },
                  { field: "v1v2", type: "ordinal" },
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
                ]
              : [
                  { field: "mu_name", type: "nominal", title: "Matchup" },
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
          }),
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
              title: opponent ? "Against " + opponent + " as" : "Against",
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
              tooltip: hasVersions
                ? [
                    { field: "mu_name", type: "nominal", title: "Matchup" },
                    { field: "v1v2", type: "ordinal" },
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
                  ]
                : [
                    { field: "mu_name", type: "nominal", title: "Matchup" },
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
        $schema: "https://vega.github.io/schema/vega-lite/v4.json",
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

      vegaEmbed("#vis", vlMUs)
        .then(function () {
          loading.style.display = "none";
        })
        .catch(console.error);
    }, 10);

    setTimeout(function () {
      var playerName = playerInput.value;
      var opponentName = opponentInput.value;
      var data = Object.entries(playerSkill).flatMap(([player, skill]) =>
        Object.entries(skill).flatMap(([char, vals]) =>
          vals.played > 0
            ? [
                {
                  ...vals,
                  player,
                  char,
                  active:
                    player === playerName
                      ? "player"
                      : opponentName === player
                      ? "opponent"
                      : "Top 20",
                },
              ]
            : []
        )
      );
      var spec = {
        data: { values: data },
        $schema: "https://vega.github.io/schema/vega-lite/v4.json",
        transform: [
          {
            window: [
              {
                op: "rank",
                as: "rank",
              },
            ],
            sort: [{ field: "mean", order: "descending" }],
            groupby: ["char"],
          },
          {
            filter:
              "datum.rank <= 20 || datum.active == 'player' || datum.active == 'opponent'",
          },
        ],
        facet: { field: "char", type: "nominal" },
        columns: 5,
        spec: {
          width: 250,
          height: 150,
          layer: [
            {
              mark: {
                type: "errorbar",
              },
              encoding: {
                y: { field: "mean", type: "quantitative" },
                yError: { field: "std" },
                x: { field: "rank", type: "ordinal" },
              },
            },
            {
              mark: {
                type: "point",
                tooltip: { content: "data" },
              },
              encoding: {
                fill: { field: "active", type: "nominal" },
                stroke: { field: "active", type: "nominal" },
                shape: { field: "active", type: "nominal" },
                y: { field: "mean", type: "quantitative" },
                x: { field: "rank", type: "ordinal" },
              },
            },
          ],
        },
      };
      vegaEmbed("#char-skill-vis", spec);
    }, 10);

    if (player) {
      var playerFetch = fetch(
        encodeURI(staticRoot + "/" + game + "/playerData/" + player + ".json")
      ).then(function (response) {
        return response.json();
      });
      if (opponent) {
        var opponentFetch = fetch(
          encodeURI(
            staticRoot + "/" + game + "/playerData/" + opponent + ".json"
          )
        ).then(function (response) {
          return response.json();
        });
      } else {
        var opponentFetch = [];
      }
      Promise.all([playerFetch, opponentFetch]).then(function (matches) {
        const playerMatches = matches[0];
        const opponentMatches = matches[1];
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
              (match.elo_after_p || opponentMatches[idx + 1].elo_before_p) -
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
                          { op: "min", field: "index", as: "index" },
                          { op: "mean", field: "eloDelta", as: "eloDelta" },
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
                      test:
                        "datum.eloDelta > 0 && datum.elo_before_p > datum.elo_before_o",
                      value: "#050",
                    },
                    {
                      test:
                        "datum.eloDelta > 0 && datum.elo_before_p < datum.elo_before_o",
                      value: "#0d0",
                    },
                    {
                      test:
                        "datum.eloDelta < 0 && datum.elo_before_p < datum.elo_before_o",
                      value: "#500",
                    },
                  ],
                  value: "#d00",
                },
                tooltip: game == "bacon" ? baconEloTooltips : yomiEloTooltips,
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
                tooltip: game == "bacon" ? baconEloTooltips : yomiEloTooltips,
              },
            },
          ],
        };

        vegaEmbed("#player-vis", vlMatches);
      });
    }
  }

  function doGraph(event) {
    comparePlayers(playerInput.value, opponentInput.value, false);
  }

  function doText(event) {
    comparePlayers(playerInput.value, opponentInput.value, true);
  }

  function doCSV(event) {
    exportCSV(playerInput.value, opponentInput.value);
  }
  window.doGraph = doGraph;
  window.doText = doText;
  window.doCSV = doCSV;

  updatePlayerStats();
  doGraph();
});
