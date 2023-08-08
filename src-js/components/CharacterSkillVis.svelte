<script lang="ts">
    import { getContext, onMount } from "svelte";
    import embed from "vega-embed";

    async function renderCharSkill(
        game: string,
        player?: string,
        opponent?: string
    ) {
        const playerSkill: PlayerSkill =
            player &&
            (await import(`../data/${game}/player/${player}/skill.json`));

        const opponentSkill: PlayerSkill =
            opponent &&
            (await import(`../data/${game}/player/${opponent}/skill.json`));

        console.log({
            aggregateSkill,
            entries: Object.entries(aggregateSkill.characters),
        });

        var data = Object.entries(aggregateSkill.characters).flatMap(
            ([character, skill]) => {
                return skill.glicko.top20.map((topSkill, rank) => ({
                    mean: topSkill.r,
                    dev: 2 * topSkill.rd,
                    character,
                    player: topSkill.player,
                    rank,
                    type: "top",
                }));
            }
        );
        var playerData =
            (playerSkill &&
                Object.entries(playerSkill.char).map(([character, skill]) => ({
                    character,
                    player,
                    mean: skill.glickoR || skill.elo,
                    dev: 2 * skill.glickoRD || 0,
                    rank: 21,
                    type: "player",
                }))) ||
            [];

        var opponentData =
            (opponentSkill &&
                Object.entries(opponentSkill.char).map(
                    ([character, skill]) => ({
                        character,
                        opponent,
                        mean: skill.glickoR || skill.elo,
                        dev: 2 * skill.glickoRD || 0,
                        rank: 22,
                        type: "opponent",
                    })
                )) ||
            [];
        var spec = {
            data: { values: data.concat(playerData, opponentData) },
            $schema: "https://vega.github.io/schema/vega-lite/v4.json",
            facet: { field: "character", type: "nominal" },
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
                            y: {
                                field: "mean",
                                type: "quantitative",
                                scale: { zero: false },
                            },
                            yError: { field: "dev" },
                            x: { field: "rank", type: "ordinal" },
                        },
                    },
                    {
                        mark: {
                            type: "point",
                            tooltip: { content: "data" },
                        },
                        encoding: {
                            fill: { field: "type", type: "nominal" },
                            stroke: { field: "type", type: "nominal" },
                            shape: { field: "type", type: "nominal" },
                            y: { field: "mean", type: "quantitative" },
                            x: { field: "rank", type: "ordinal" },
                        },
                    },
                ],
            },
        };
        embed("#char-skill-vis", spec);
    }

    export let game: string;
    export let player: string;
    export let opponent: string;
    export let aggregateSkill: AggregatePlayerSkill;

    $: mounted && renderCharSkill(game, player, opponent);
    let mounted = false;
    onMount(() => {
        mounted = true;
    });
</script>

<div id="char-skill-vis" />
