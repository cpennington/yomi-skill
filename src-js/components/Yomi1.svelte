<script lang="ts">
  import PlayerSelector from "./PlayerSelector.svelte";
  import AgainstConfig from "./AgainstConfig.svelte";
  import PlayerStats from "./PlayerStats.svelte";
  import MatchupVis from "./MatchupVis.svelte";
  import CharacterSkillVis from "./CharacterSkillVis.svelte";
  import PlayerHistoryVis from "./PlayerHistoryVis.svelte";
  import type {
    AggregatePlayerSkill,
    CharacterPlayCounts,
    MatchupData,
    Scales,
  } from "$lib/types";

  const game = "yomi";
  export let matchupData: MatchupData;
  export let characters: CharacterPlayCounts;
  export let scales: Scales;
  export let aggregateSkill: AggregatePlayerSkill;
  export let players: Record<string, number>;

  let againstRating: "self" | number = "self";
  let againstCharRating: "self" | number = "self";

  let player = "";
  let opponent = "";
</script>

<div class="grid grid-template-column max-w-6xl place-content-center">
  <PlayerSelector
    {players}
    loading={!(characters && matchupData && scales)}
    bind:player
    bind:opponent
  />
  {#if player && !opponent}
    <AgainstConfig bind:againstRating bind:againstCharRating />
  {/if}
  <PlayerStats {game} {player} {opponent} />

  <div class="row col-12">
    <p class="col-12 mt-4">
      If you'd like to improve the matchup chart, play tournament games on the
      <a href="https://forums.sirlingames.com/c/yomi">Sirlin Games Forum!</a>
    </p>
  </div>
</div>
{#if characters && matchupData && aggregateSkill}
  <div>
    <MatchupVis
      {characters}
      {matchupData}
      {scales}
      {player}
      {opponent}
      {againstRating}
      {againstCharRating}
      {aggregateSkill}
      {game}
    />
  </div>
{/if}

{#if aggregateSkill}
  <div>
    <CharacterSkillVis
      {characters}
      {aggregateSkill}
      {player}
      {opponent}
      {game}
    />
  </div>
{/if}
{#if player}
  <div>
    <PlayerHistoryVis {player} {opponent} {game} />
  </div>
{/if}
