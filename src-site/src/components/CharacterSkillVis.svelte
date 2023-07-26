<script>
    export let playerSkill;
    export let playerName;
    export let opponentName;

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
                filter: "datum.rank <= 20 || datum.active == 'player' || datum.active == 'opponent'",
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
    embed("#char-skill-vis", spec);
</script>

<div id="char-skill-vis" />
