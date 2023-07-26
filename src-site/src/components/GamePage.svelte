<script lang="ts">
  import loading from "../assets/loading.svg";
  import gaussian from "gaussian";
  import PlayerSelector from "./PlayerSelector.svelte";
  import AgainstConfig from "./AgainstConfig.svelte";
  import { getContext, onMount, setContext } from "svelte";
  import NewDataCta from "./NewDataCTA.svelte";
  import PlayerStats from "./PlayerStats.svelte";
  import MatchupVis from "./MatchupVis.svelte";
  import CharacterSkillVis from "./CharacterSkillVis.svelte";
  import PlayerHistoryVis from "./PlayerHistoryVis.svelte";

  export let game;

  export let matchupData;
  export let characters;
  export let scales;
  export let playerSkill;
  export let players;

  let againstElo: "self" | number = "self";
  let againstCharElo: "self" | number = "self";

  let playerName = "";
  let opponentName = "";
</script>

<div class="grid grid-template-column max-w-6xl place-content-center">
  <PlayerSelector
    {players}
    loading={!(characters && matchupData && scales)}
    bind:player={playerName}
    bind:opponent={opponentName}
  />
  {#if playerName && !opponentName}
    <AgainstConfig bind:againstElo bind:againstCharElo />
  {/if}
  <PlayerStats />
  <NewDataCta {game} />
  {#if playerName}
    <PlayerHistoryVis player={playerName} {game} />
  {/if}
</div>
{#if characters && matchupData}
  <MatchupVis
    {characters}
    {matchupData}
    {scales}
    player={playerName}
    opponent={opponentName}
    {againstElo}
    {againstCharElo}
    {playerSkill}
    textOnly={false}
  />
{/if}

<!-- {#if playerSkill && playerName && opponentName}
  <CharacterSkillVis {playerSkill} {playerName} {opponentName} />
{/if} -->

<style>
  @keyframes rotate {
    from {
      transform: rotate(0deg);
    }

    to {
      transform: rotate(-360deg);
    }
  }

  #arrows {
    height: 20px;
    transform-origin: center center;
    animation-name: rotate;
    animation-duration: 5s;
    animation-iteration-count: infinite;
    animation-timing-function: linear;
  }

  #c2-total {
    padding-left: 46px;
  }

  #total {
    padding-left: 15px;
  }
</style>
