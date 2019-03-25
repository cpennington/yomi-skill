const matchupData = JSON.parse(
  document.getElementById("matchup-data").innerText
);
const characters = JSON.parse(document.getElementById("characters").innerText);
const playerSkill = JSON.parse(
  document.getElementById("player-skill").innerText
);
const eloScale = JSON.parse(document.getElementById("elo-scale").innerText);
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

playerInput.onblur = updatePlayerStats;
opponentInput.onblur = updatePlayerStats;

const quantiles = [0.05, 0.25, 0.5, 0.75, 0.95, 1];
const medianPlayerSkill = {};
const medianPlayerElo = {};
characters.forEach(function(char) {
  medianPlayerSkill[char] = {};
  skillQValues = math.quantileSeq(
    Object.entries(playerSkill)
      .map(function(skillsByChar) {
        var charStats = skillsByChar[1][char];
        if (charStats) {
          return charStats.mean;
        } else {
          return null;
        }
      })
      .filter(function(v) {
        return v != null;
      }),
    quantiles
  );

  std = math.mean(
    Object.entries(playerSkill)
      .map(function(skillsByChar) {
        var charStats = skillsByChar[1][char];
        if (charStats) {
          return charStats.std;
        } else {
          return null;
        }
      })
      .filter(function(v) {
        return v != null;
      })
  );

  eloQValues = math.quantileSeq(
    Object.values(playerSkill)
      .map(function(skill) {
        return skill.elo;
      })
      .filter(function(v) {
        return v >= 0;
      }),
    quantiles
  );

  quantiles.forEach(function(q, idx) {
    medianPlayerSkill[char][q * 100 + "%"] = {
      mean: skillQValues[idx],
      std: std
    };
    medianPlayerElo[q * 100 + "%"] = eloQValues[idx];
  });
});

Object.entries(playerSkill)
  .map(function(entry) {
    return [entry[1].gamesPlayed, entry[0]];
  })
  .sort(function(a, b) {
    return a[0] < b[0];
  })
  .forEach(function(entry) {
    var opt = document.createElement("option");
    opt.value = entry[1];
    opt.textContent = entry[1] + " (" + entry[0] + " games recorded)";
    playersList.appendChild(opt);
  });

var xs = [];
for (x = 0; x <= 1; x += increment) {
  xs.push(x);
}

var percPts = [];
for (pp = 0; pp <= 1; pp += 0.001) {
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

function muPDF(mu, player, opponent) {
  var pdf = xs.map(function(x) {
    var muDist = gaussian(mu.mean, mu.std * mu.std);
    var dist = muDist;
    if (player) {
      const pSkill = playerSkill[player][mu.c1];
      const pSkillDist = gaussian(pSkill.mean, pSkill.std * pSkill.std);
      if (opponent) {
        const oSkill = playerSkill[opponent][mu.c2];
        const oSkillDist = gaussian(oSkill.mean, oSkill.std * oSkill.std);

        const eloDiff = playerSkill[player].elo - playerSkill[opponent].elo;
        eloPctPlayerWin = 1 / (1 + Math.pow(10, -eloDiff / 1135.77));
        eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));

        poDist = muDist
          .add(pSkillDist)
          .sub(oSkillDist)
          .add(eloScaleDist.scale(eloLogit));
      } else {
        const againstSkillPick = Array.from(
          document.getElementsByName("against-skill")
        )
          .map(function(e) {
            return e.checked ? e.value : null;
          })
          .filter(function(v) {
            return v != null;
          })[0];
        var oSkill;
        if (againstSkillPick === "self") {
          oSkill = {
            mean: math.mean(
              characters.map(function(char) {
                return playerSkill[player][char].mean;
              })
            ),
            std: math.mean(
              characters.map(function(char) {
                return playerSkill[player][char].std;
              })
            )
          };
        } else {
          oSkill = medianPlayerSkill[mu.c2][againstSkillPick];
        }
        const oSkillDist = gaussian(oSkill.mean, oSkill.std * oSkill.std);

        const againstEloPick = Array.from(
          document.getElementsByName("against-elo")
        )
          .map(function(e) {
            return e.checked ? e.value : null;
          })
          .filter(function(v) {
            return v != null;
          })[0];
        var eloDiff;
        if (againstEloPick === "self") {
          eloDiff = 0;
        } else {
          eloDiff = playerSkill[player].elo - medianPlayerElo[againstEloPick];
        }

        eloPctPlayerWin = 1 / (1 + Math.pow(10, -eloDiff / 1135.77));
        eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));

        poDist = muDist.add(pSkillDist).sub(oSkillDist);
        if (eloDiff != 0) {
          poDist = poDist.add(eloScaleDist.scale(eloLogit));
        }
      }
      dist = poDist;
    }
    const upper = dist.cdf(logOdds(x + increment / 2));
    const lower = dist.cdf(logOdds(x - increment / 2));

    var datum = {
      c1: mu.c1,
      c2: mu.c2,
      mu: formatMU(x),
      winChance: x,
      credLower: invLogOdds(dist.ppf(0.05)),
      credUpper: invLogOdds(dist.ppf(0.95)),
      pdf: dist.pdf(logOdds(x)),
      p: upper - lower,
      type: player ? "match" : "global",
      count: mu.counts
    };
    if (player) {
      datum.pCount = playerSkill[player][mu.c1].played;
      if (opponent) {
        datum.oCount = playerSkill[opponent][mu.c2].played;
      }
      datum.player = player;
    }
    if (opponent) {
      datum.opponent = opponent;
    }
    return datum;
  });
  return pdf;
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

function comparePlayers(player, opponent) {
  loading.style.display = "inline";
  vis.style.display = "none";

  setTimeout(function() {
    muEstimates = matchupData.flatMap(function(v) {
      var pdf = [];
      if (v.c1 != v.c2) {
        pdf = pdf.concat(muPDF(v));
      }
      if (player) {
        pdf = pdf.concat(muPDF(v, player, opponent));
      }
      return pdf;
    });

    const muEstimate = {
      title: "Matchup Estimate",
      field: "mu",
      type: "ordinal",
      axis: {
        labels: true,
        title: null,
        values: ["2-8", "5-5", "8-2"],
        grid: true,
        gridOpacity: 0.5
      }
    };
    const muLikelihood = {
      title: "Likelihood of Matchup Estimate",
      field: "p",
      type: "quantitative",
      axis: { labels: false, title: null },
      format: ".0%",
      stack: null
    };
    const overallWinChance = Object.assign(
      {},
      {
        title: "Aggregate Win Estimate",
        field: "cum_p",
        type: "quantitative",
        scale: {
          scheme: [
            "rgb(48, 48, 255)",
            "rgb(230, 164, 230)",
            "rgb(255, 61, 61)"
          ],
          domain: [0.3, 0.7],
          clamp: true
        },
        format: ".0%",
        legend: {
          format: ".0%"
        }
      },
      player
        ? {
            condition: {
              test: "datum['type'] == 'global'",
              value: "transparent"
            }
          }
        : {}
    );
    const statsType = { field: "type", type: "nominal" };
    const muCount = {
      field: "count",
      type: "quantitative",
      title: "MU Games Recorded"
    };
    const pCount = {
      field: "pCount",
      type: "quantitative",
      title: "Player-Character Games Recorded",
      condition: { test: "datum['pCount'] !== null" }
    };
    const oCount = {
      field: "oCount",
      type: "quantitative",
      title: "Opponent-Character Games Recorded",
      condition: { test: "datum['oCount'] !== null" }
    };
    const credInterval = {
      field: "credInterval",
      type: "ordinal",
      title: "90% Chance MU Within"
    };

    const stroke = player
      ? {
          condition: {
            test: "datum['type'] == 'global'",
            value: "#000"
          },
          value: "transparent"
        }
      : {
          value: "transparent"
        };

    const pdf = {
      field: "pdf",
      type: "quantitative",
      stack: null,
      axis: { labels: false, title: null, tickCount: 2, gridOpacity: 0.5 },
      scale: {
        domain: [
          0,
          math.max(
            muEstimates.map(function(datum) {
              return datum.pdf;
            })
          )
        ]
      }
    };

    const mark = {
      type: "area",
      stroke: "#000",
      interpolate: "monotone"
    };

    const baseEncoding = {
      x: muEstimate,
      y: pdf,
      fill: overallWinChance,
      stroke: stroke,
      detail: statsType,
      tooltip: [
        statsType,
        credInterval,
        overallWinChance,
        { field: "muLikelihood", type: "nominal", title: "Estimate" },
        muCount
      ]
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
      as: "credInterval"
    };

    const muLikelihoodTransform = {
      calculate:
        "join([" +
        "format(datum.p, '.0%')," +
        "'chance the MU is'," +
        "datum.mu" +
        "], ' ')",
      as: "muLikelihood"
    };

    const vlC1C2 = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: muEstimates
      },
      config: {
        facet: {
          spacing: {
            row: 0,
            column: 0
          }
        }
      },
      vconcat: [
        {
          hconcat: [
            {
              transform: [
                {
                  calculate: "datum.p * datum.winChance",
                  as: "w_p"
                },
                {
                  joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" }
                  ],
                  groupby: ["c1", "c2", "type"]
                },
                {
                  calculate: "abs(datum.signed_cum_p)",
                  as: "cum_p"
                },
                {
                  calculate: "join([datum.c1, '/', datum.c2], '')",
                  as: "mu_name"
                },
                credIntervalTransform,
                muLikelihoodTransform
              ],
              facet: {
                row: {
                  field: "c1",
                  type: "ordinal",
                  header: {
                    title: player ? player + " playing " : "Playing",
                    labelLimit: 40
                  }
                },
                column: {
                  field: "c2",
                  type: "ordinal",
                  header: {
                    title: opponent ? "Against " + opponent + " as" : "Against",
                    labelLimit: 40
                  }
                }
              },
              spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: Object.assign({}, baseEncoding, {
                  tooltip: [
                    { field: "mu_name", type: "nominal", title: "Matchup" },
                    statsType,
                    credInterval,
                    overallWinChance,
                    {
                      field: "muLikelihood",
                      type: "nominal",
                      title: "Estimate"
                    },
                    muCount,
                    pCount,
                    oCount
                  ]
                })
              }
            },
            {
              transform: [
                {
                  aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "sum", field: "count", as: "count" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" },
                    { op: "mean", field: "pCount", as: "pCount" }
                  ],
                  groupby: ["c1", "mu", "type"]
                },
                {
                  calculate: "datum.sum_p / " + characters.length,
                  as: "p"
                },
                {
                  calculate: "datum.sum_pdf / " + characters.length,
                  as: "pdf"
                },
                {
                  calculate: "datum.p * datum.mean_win_chance",
                  as: "w_p"
                },
                {
                  joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" }
                  ],
                  groupby: ["c1", "type"]
                },
                {
                  calculate: "abs(datum.signed_cum_p)",
                  as: "cum_p"
                },
                credIntervalTransform,
                muLikelihoodTransform
              ],
              facet: {
                row: {
                  field: "c1",
                  type: "ordinal",
                  header: { title: null, labelLimit: 40 }
                }
              },
              spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: Object.assign({}, baseEncoding, {
                  tooltip: [
                    statsType,
                    credInterval,
                    overallWinChance,
                    {
                      field: "muLikelihood",
                      type: "nominal",
                      title: "Estimate"
                    },
                    muCount,
                    pCount
                  ]
                })
              }
            }
          ]
        },
        {
          hconcat: [
            {
              transform: [
                {
                  aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "sum", field: "count", as: "count" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" },
                    { op: "mean", field: "oCount", as: "oCount" }
                  ],
                  groupby: ["c2", "mu", "type"]
                },
                {
                  calculate: "datum.sum_p / " + characters.length,
                  as: "p"
                },
                {
                  calculate: "datum.sum_pdf / " + characters.length,
                  as: "pdf"
                },
                {
                  calculate: "datum.p * datum.mean_win_chance",
                  as: "w_p"
                },
                {
                  joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" }
                  ],
                  groupby: ["c2", "type"]
                },
                {
                  calculate: "abs(datum.signed_cum_p)",
                  as: "cum_p"
                },
                credIntervalTransform,
                muLikelihoodTransform
              ],

              facet: {
                column: {
                  field: "c2",
                  type: "ordinal",
                  header: { title: null, labelLimit: 40 }
                }
              },
              spec: {
                width: 50,
                height: 40,
                mark: mark,
                encoding: Object.assign({}, baseEncoding, {
                  tooltip: [
                    statsType,
                    credInterval,
                    overallWinChance,
                    {
                      field: "muLikelihood",
                      type: "nominal",
                      title: "Estimate"
                    },
                    muCount,
                    oCount
                  ]
                })
              }
            },
            {
              transform: [
                {
                  aggregate: [
                    { op: "sum", field: "p", as: "sum_p" },
                    { op: "sum", field: "pdf", as: "sum_pdf" },
                    { op: "mean", field: "winChance", as: "mean_win_chance" },
                    { op: "mean", field: "credLower", as: "credLower" },
                    { op: "mean", field: "credUpper", as: "credUpper" }
                  ],
                  groupby: ["mu", "type"]
                },
                {
                  calculate:
                    "datum.sum_p / " + characters.length * characters.length,
                  as: "p"
                },
                {
                  calculate:
                    "datum.sum_pdf / " + characters.length * characters.length,
                  as: "pdf"
                },
                {
                  calculate: "datum.p * datum.mean_win_chance",
                  as: "w_p"
                },
                {
                  joinaggregate: [
                    { op: "sum", field: "w_p", as: "signed_cum_p" }
                  ],
                  groupby: ["type"]
                },
                {
                  calculate: "abs(datum.signed_cum_p)",
                  as: "cum_p"
                },
                credIntervalTransform,
                muLikelihoodTransform
              ],
              width: 50,
              height: 40,
              mark: mark,
              encoding: baseEncoding
            }
          ]
        }
      ]
    };

    vegaEmbed("#vis", vlC1C2)
      .then(function() {
        loading.style.display = "none";
        delete vis.style.display;
      })
      .catch(console.error);
  }, 10);
}

function doGraph(event) {
  comparePlayers(playerInput.value, opponentInput.value);
}

updatePlayerStats();
doGraph();
