<script lang="ts">
    import type { PlayerSkill } from "$lib/types";

    let pSkill: Promise<PlayerSkill> | null;
    let oSkill: Promise<PlayerSkill> | null;

    export let player: string;
    export let opponent: string;
    export let game: string;

    $: pSkill = player
        ? import(`../data/${game}/player/${player}/skill.json`)
        : null;
    $: oSkill = opponent
        ? import(`../data/${game}/player/${opponent}/skill.json`)
        : null;

    $: console.log({ player, opponent, pSkill, oSkill });
</script>

<table id="player-stats" class="table-auto">
    <thead class="border-b-2">
        <tr>
            <th class="text-left">Player</th>
            <th class="text-left">Rating</th>
            <th class="text-left">Games recorded</th>
        </tr>
    </thead>
    <tbody class="divide-y">
        {#if pSkill}
            {#await pSkill then skill}
                <tr id="p1-stats">
                    <td class="text-left">{player}</td>
                    <td class="text-left">
                        {#if "elo" in skill && skill.elo}
                            {Math.round(skill.elo)}
                        {/if}
                        {#if "glickoR" in skill && skill.glickoR}
                            {Math.round(skill.glickoR)} +/- {Math.round(
                                skill.glickoRD
                            )}
                        {/if}
                    </td><td class="text-left">{skill.gamesPlayed}</td>
                </tr>
            {/await}
        {/if}
        {#if oSkill}
            {#await oSkill then skill}
                <tr id="p2-stats" class="border-b-1">
                    <td class="text-left">{opponent}</td>
                    <td class="text-left">
                        {#if "elo" in skill && skill.elo}
                            {Math.round(skill.elo)}
                        {/if}
                        {#if "glickoR" in skill && skill.glickoR}
                            {Math.round(skill.glickoR)} +/- {Math.round(
                                skill.glickoRD
                            )}
                        {/if}
                    </td><td class="text-left">{skill.gamesPlayed}</td>
                </tr>
            {/await}
        {/if}
    </tbody>
</table>
