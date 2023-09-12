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
    PlayerSummary,
    Scales,
  } from "$lib/types";
  import GemVis from "./GemVis.svelte";
  import PlayerRanking from "./PlayerRanking.svelte";
  import Yomi2Upload from "./Yomi2Upload.svelte";

  const game = "yomi2";
  export let matchupData: MatchupData;
  export let characters: CharacterPlayCounts;
  export let scales: Scales;
  export let aggregateSkill: AggregatePlayerSkill;
  export let players: PlayerSummary;
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
  <!-- {#if player && !opponent}
    <AgainstConfig bind:againstRating bind:againstCharRating />
  {/if} -->
  <PlayerStats {game} {player} {opponent} />

  <Yomi2Upload />
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

<PlayerRanking {players} />
