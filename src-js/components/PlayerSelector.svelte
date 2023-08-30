<script lang="ts">
  import type { PlayerSummary } from "$lib/types";
  export let loading = true;
  import loadingSVG from "../assets/loading.svg";

  // playerInput.onblur = updatePlayerStats;
  // opponentInput.onblur = updatePlayerStats;
  export let players: PlayerSummary;
  export let player: string;
  export let opponent: string;

  let playCounts: [string, number][] = [];
  $: {
    playCounts = [...players]
      .sort((a, b) => b.gamesPlayed - a.gamesPlayed)
      .map((player) => [player.player, player.gamesPlayed]);
  }
</script>

<div class="div-group grid grid-cols-12 mt-2 space-x-1 p-1">
  <label for="player" class="grid col-span-1 p-1">Player:</label>
  <input
    list="players"
    id="player"
    name="player"
    class="grid col-span-3 border-2 border-slate-500 rounded-md p-1"
    on:blur={(e) => (player = e.target.value)}
  />
  <label for="opponent" class="grid col-span-1 p-1">Opponent:</label>
  <input
    list="players"
    id="opponent"
    name="opponent"
    class="grid col-span-3 border-2 border-slate-500 rounded-md p-1"
    on:blur={(e) => (opponent = e.target.value)}
  />
  <div class="grid col-span-3 grid-cols-12">
    {#if loading}
      <div id="loading" class="col-span-1 justify-content-end">
        <img
          id="arrows"
          class="h-5 animate-spin"
          src={loadingSVG.src}
          alt="Loading..."
        />
      </div>
    {/if}
  </div>
  <datalist id="players">
    {#each playCounts as [player, count]}
      <option value={player}>{player} ({count} games recorded)</option>
    {/each}
  </datalist>
</div>
