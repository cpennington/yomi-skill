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
const increment = 0.05;

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

function log_odds(win_chance) {
  return Math.log(win_chance / (1 - win_chance));
}
function normal_dist(mean, std, x) {
  variance = std * std;

  return (
    (1 / Math.sqrt(2 * Math.PI * variance)) *
    Math.exp(-Math.pow(x - mean, 2) / (2 * variance))
  );
}
function mu_pdf(mu, player, opponent) {
  var pdf = xs.map(function(x) {
    var dist = gaussian(mu.mean, mu.std * mu.std);
    if (player && opponent) {
      const pSkill = playerSkill[player][mu.c1];
      const pSkillDist = gaussian(pSkill.mean, pSkill.std * pSkill.std);
      const oSkill = playerSkill[opponent][mu.c2];
      const oSkillDist = gaussian(oSkill.mean, oSkill.std * oSkill.std);

      const eloDiff = playerSkill[player].elo - playerSkill[opponent].elo;
      eloPctPlayerWin = 1 / (1 + Math.pow(10, -eloDiff / 1135.77));
      eloLogit = Math.log(eloPctPlayerWin / (1 - eloPctPlayerWin));

      dist = dist
        .add(pSkillDist)
        .sub(oSkillDist)
        .add(eloScaleDist.scale(eloLogit));
    }
    const upper = dist.cdf(log_odds(x + increment / 2));
    const lower = dist.cdf(log_odds(x - increment / 2));
    var datum = {
      c1: mu.c1,
      c2: mu.c2,
      mu: Math.round(x * 100) / 10 + "-" + (10 - Math.round(x * 100) / 10),
      win_chance: x,
      p: player && opponent ? -(upper - lower) : upper - lower,
      type: player && opponent ? "match" : "global",
      count: mu.counts
    };
    if (player && opponent) {
      datum.pCount = playerSkill[player][mu.c1].played;
      datum.oCount = playerSkill[opponent][mu.c2].played;
    }
    return datum;
  });
  return pdf;
}

function comparePlayers(player, opponent) {
  loading.style.display = "inline";
  vis.style.display = "none";

  if (player) {
    document.getElementById("p1-name").textContent = player;
    document.getElementById("p1-elo").textContent = Math.round(
      playerSkill[player].elo
    );
    document.getElementById("p1-games").textContent =
      playerSkill[player].gamesPlayed;
  }
  if (opponent) {
    document.getElementById("p2-name").textContent = opponent;
    document.getElementById("p2-elo").textContent = Math.round(
      playerSkill[opponent].elo
    );
    document.getElementById("p2-games").textContent =
      playerSkill[opponent].gamesPlayed;
  }

  setTimeout(function() {
    values = matchupData.flatMap(function(v) {
      var pdf = mu_pdf(v);
      if (player && opponent) {
        pdf = pdf.concat(mu_pdf(v, player, opponent));
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
        values: ["5-5"]
      }
    };
    const muLikelihood = {
      title: "Likelihood of Matchup Estimate",
      field: "p",
      type: "quantitative",
      axis: { labels: false, title: null },
      format: ".1%"
    };
    const overallWinChance = {
      title: "Overall Win Chance",
      field: "cum_p",
      type: "quantitative",
      scale: {
        scheme: ["rgb(48, 48, 255)", "rgb(230, 164, 230)", "rgb(255, 61, 61)"],
        domain: [0.3, 0.7],
        clamp: true
      },
      format: ".1%",
      legend: null
    };
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

    const vlC1C2 = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: values
      },
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
      spacing: {
        row: 2,
        column: 2
      },
      transform: [
        {
          calculate: "datum.p * datum.win_chance",
          as: "w_p"
        },
        {
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
          groupby: ["c1", "c2", "type"]
        },
        {
          calculate: "abs(datum.signed_cum_p)",
          as: "cum_p"
        }
      ],
      spec: {
        width: 50,
        height: 40,
        mark: {
          type: "bar"
        },
        encoding: {
          x: muEstimate,
          y: muLikelihood,
          color: overallWinChance,
          detail: statsType,
          tooltip: [
            statsType,
            overallWinChance,
            muEstimate,
            muLikelihood,
            muCount,
            pCount,
            oCount
          ]
        }
      }
    };

    const vlC1Totals = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: values
      },
      transform: [
        {
          aggregate: [
            { op: "sum", field: "p", as: "sum_p" },
            { op: "mean", field: "win_chance", as: "mean_win_chance" }
          ],
          groupby: ["c1", "mu", "type"]
        },
        {
          calculate: "datum.sum_p / " + characters.length,
          as: "p"
        },
        {
          calculate: "datum.p * datum.mean_win_chance",
          as: "w_p"
        },
        {
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
          groupby: ["c1", "type"]
        },
        {
          calculate: "abs(datum.signed_cum_p)",
          as: "cum_p"
        }
      ],
      facet: {
        row: {
          field: "c1",
          type: "ordinal",
          header: { title: null, labelLimit: 40 }
        }
      },
      spacing: {
        row: 2,
        column: 2
      },
      spec: {
        width: 50,
        height: 40,
        mark: {
          type: "bar"
        },
        encoding: {
          x: {
            title: "Matchup Estimate",
            field: "mu",
            type: "ordinal",
            axis: {
              labels: true,
              title: null,
              values: ["5-5"]
            }
          },
          y: {
            title: "Likelihood of Matchup Estimate",
            field: "p",
            type: "quantitative",
            axis: { labels: false, title: null },
            format: ".1%"
          },
          color: {
            title: "Overall Win Chance",
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
            format: ".1%",
            legend: { format: ".1%" }
          },
          detail: { field: "type", type: "nominal" }
        }
      }
    };

    const vlC2Totals = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: values
      },
      transform: [
        {
          aggregate: [
            { op: "sum", field: "p", as: "sum_p" },
            { op: "mean", field: "win_chance", as: "mean_win_chance" }
          ],
          groupby: ["c2", "mu", "type"]
        },
        {
          calculate: "datum.sum_p / " + characters.length,
          as: "p"
        },
        {
          calculate: "datum.p * datum.mean_win_chance",
          as: "w_p"
        },
        {
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
          groupby: ["c2", "type"]
        },
        {
          calculate: "abs(datum.signed_cum_p)",
          as: "cum_p"
        }
      ],

      facet: {
        column: {
          field: "c2",
          type: "ordinal",
          header: { title: null, labelLimit: 40 }
        }
      },
      spacing: {
        row: 2,
        column: 2
      },
      spec: {
        width: 50,
        height: 40,
        mark: {
          type: "bar"
        },
        encoding: {
          x: {
            title: "Matchup Estimate",
            field: "mu",
            type: "ordinal",
            axis: {
              labels: true,
              title: null,
              values: ["5-5"]
            }
          },
          y: {
            title: "Likelihood of Matchup Estimate",
            field: "p",
            type: "quantitative",
            axis: { labels: false, title: null },
            format: ".1%"
          },
          color: {
            title: "Overall Win Chance",
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
            format: ".1%",
            legend: null
          },
          detail: { field: "type", type: "nominal" }
        }
      }
    };

    const vlTotals = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: values
      },
      transform: [
        {
          aggregate: [
            { op: "sum", field: "p", as: "sum_p" },
            { op: "mean", field: "win_chance", as: "mean_win_chance" }
          ],
          groupby: ["mu", "type"]
        },
        {
          calculate: "datum.sum_p / " + characters.length * characters.length,
          as: "p"
        },
        {
          calculate: "datum.p * datum.mean_win_chance",
          as: "w_p"
        },
        {
          joinaggregate: [{ op: "sum", field: "w_p", as: "signed_cum_p" }],
          groupby: ["type"]
        },
        {
          calculate: "abs(datum.signed_cum_p)",
          as: "cum_p"
        }
      ],

      width: 50,
      height: 40,
      mark: {
        type: "bar"
      },
      encoding: {
        x: {
          title: "Matchup Estimate",
          field: "mu",
          type: "ordinal",
          axis: {
            labels: true,
            title: null,
            values: ["5-5"]
          }
        },
        y: {
          title: "Likelihood of Matchup Estimate",
          field: "p",
          type: "quantitative",
          axis: { labels: false, title: null },
          format: ".1%"
        },
        color: {
          title: "Overall Win Chance",
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
          format: ".1%",
          legend: null
        },
        detail: { field: "type", type: "nominal" }
      }
    };

    Promise.all([
      vegaEmbed("#c1-c2", vlC1C2),
      vegaEmbed("#c1-total", vlC1Totals).then(function(embed) {
        console.log(embed.view.data("data_0"));
      }),
      vegaEmbed("#c2-total", vlC2Totals),
      vegaEmbed("#total", vlTotals)
    ])
      .then(function() {
        loading.style.display = "none";
        vis.style.display = "block";
        vis.style.width =
          document.getElementById("c1-c2").offsetWidth +
          document.getElementById("c1-total").offsetWidth +
          50 +
          "px";
      })
      .catch(console.error);
  }, 10);
}

function doGraph(event) {
  comparePlayers(playerInput.value, opponentInput.value);
}

doGraph();
