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
    GemEffects,
    MatchupData,
    Scales,
  } from "$lib/types";
  import GemVis from "./GemVis.svelte";

  const game = "yomi2";
  export let matchupData: MatchupData;
  export let characters: CharacterPlayCounts;
  export let scales: Scales;
  export let aggregateSkill: AggregatePlayerSkill;
  export let players: Record<string, number>;
  export let gemEffects: GemEffects;

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
      If you'd like to improve the matchup chart, report your matches with the
      <a href="https://forms.gle/DRMW4MAxB3dWZS1K9">Yomi 2 Match Report form</a
      >!
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
{#if gemEffects}
  <div>
    <GemVis {gemEffects} {characters} />
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
