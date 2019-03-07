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

Object.keys(playerSkill).forEach(function(p) {
  var opt = document.createElement("option");
  opt.value = p;
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
  var pdf = xs
    .map(function(x) {
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
      return {
        c1: mu.c1,
        c2: mu.c2,
        mu: Math.round(x * 100) / 10 + "-" + (10 - Math.round(x * 100) / 10),
        win_chance: x,
        p: player && opponent ? -(upper - lower) : upper - lower,
        type: player && opponent ? "match" : "global"
      };
    })
    .filter(function(d) {
      return Math.abs(d.p) > 0.005;
    });
  if (pdf.length > 0) {
    cum_p = 0;
    for (idx in pdf) {
      cum_p += pdf[idx].p * pdf[idx].win_chance;
    }
    for (idx in pdf) {
      pdf[idx].cum_p = Math.abs(cum_p);
    }
  }
  return pdf;
}

function comparePlayers(player, opponent) {
  loading.style.display = "inline";
  vis.style.display = "none";

  setTimeout(function() {
    values = matchupData.flatMap(function(v) {
      const pdf = mu_pdf(v);
      const playerPdf = mu_pdf(v, player, opponent);
      return pdf.concat(playerPdf);
    });

    var vlSpec = {
      $schema: "https://vega.github.io/schema/vega-lite/v3.json",
      data: {
        values: values
      },
      transform: [
        {
          joinaggregate: [{ op: "mean", field: "cum_p", as: "c1_avg_cum_p" }],
          groupby: ["c1"]
        },
        {
          joinaggregate: [{ op: "mean", field: "cum_p", as: "c2_avg_cum_p" }],
          groupby: ["c2"]
        }
      ],
      resolve: { scale: { color: "independent" } },
      hconcat: [
        {
          facet: {
            row: {
              field: "c1",
              type: "ordinal",
              header: { title: player ? player + " playing " : "Playing" }
            },
            column: {
              field: "c2",
              type: "ordinal",
              header: {
                title: opponent ? "Against " + opponent + " as" : "Against"
              }
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
                format: ".0%"
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
                  domain: [0.3, 0.7]
                },
                format: ".0%",
                legend: { format: ".0%" }
              },
              detail: { field: "type", type: "nominal" }
            }
          }
        },

        {
          facet: {
            row: {
              field: "c1",
              type: "ordinal",
              header: { title: player ? player + " playing " : "Playing" }
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
                aggregate: "mean",
                field: "p",
                type: "quantitative",
                axis: { labels: false, title: null },
                format: ".0%"
              },
              color: {
                title: "Overall Win Chance",
                aggregate: "mean",
                field: "c1_avg_cum_p",
                type: "quantitative",
                scale: {
                  scheme: [
                    "rgb(48, 48, 255)",
                    "rgb(230, 164, 230)",
                    "rgb(255, 61, 61)"
                  ],
                  domain: [0.3, 0.7]
                },
                format: ".0%",
                legend: { format: ".0%" }
              },
              detail: { field: "type", type: "nominal" }
            }
          }
        }
      ]
    };

    console.log(JSON.stringify(vlSpec));

    vegaEmbed("#vis", vlSpec)
      .then(function(embed) {
        window.embed = embed;
      })
      .catch(console.error);
    loading.style.display = "none";
    vis.style.display = "block";
  }, 10);
}

function doGraph(event) {
  comparePlayers(playerInput.value, opponentInput.value);
}

doGraph();
