<script lang="ts">
    import type {
        AggregatePlayerSkill,
        CharacterPlayCounts,
        PlayerSkill,
    } from "$lib/types";
    import { getContext, onMount } from "svelte";
    import embed from "vega-embed";

    async function renderCharSkill(
        characters: CharacterPlayCounts,
        game: string,
        player?: string,
        opponent?: string
    ) {
        const playedCharacters = characters
            .filter((char) => char.gamesRecorded > 0)
            .map((char) => char.character);
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

        var data = Object.entries(aggregateSkill.characters)
            .filter(([character, _]) => playedCharacters.includes(character))
            .flatMap(([character, skill]) => {
                return skill.glicko.top20.map((topSkill, rank) => ({
                    mean: topSkill.r,
                    dev: 2 * topSkill.rd,
                    character,
                    player: topSkill.player,
                    rank,
                    type: "top",
                }));
            });
        var playerData =
            (playerSkill &&
                Object.entries(playerSkill.char)
                    .filter(
                        ([character, skill]) =>
                            playedCharacters.includes(character) &&
                            skill.gamesPlayed > 0
                    )
                    .map(([character, skill]) => ({
                        character,
                        player,
                        mean: skill.glickoR || skill.elo,
                        dev: 2 * skill.glickoRD || 0,
                        rank: data.length,
                        type: "player",
                    }))) ||
            [];

        var opponentData =
            (opponentSkill &&
                Object.entries(opponentSkill.char)
                    .filter(
                        ([character, _]) =>
                            playedCharacters.includes(character) &&
                            skill.gamesPlayed > 0
                    )
                    .map(([character, skill]) => ({
                        character,
                        opponent,
                        mean: skill.glickoR || skill.elo,
                        dev: 2 * skill.glickoRD || 0,
                        rank: data.length + 1,
                        type: "opponent",
                    }))) ||
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
    export let characters: CharacterPlayCounts;

    $: mounted && renderCharSkill(characters, game, player, opponent);
    let mounted = false;
    onMount(() => {
        mounted = true;
    });
</script>

<div id="char-skill-vis" />
