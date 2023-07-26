<script>
  import { createEventDispatcher } from "svelte";
  export let loading = true;
  import loadingSVG from "../assets/loading.svg";
  // playerInput.onblur = updatePlayerStats;
  // opponentInput.onblur = updatePlayerStats;
  export let players = {};
  export let player;
  export let opponent;

  let playCounts = [];
  $: {
    playCounts = Object.entries(players).sort((a, b) => a[1] < b[1]);
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
    <button
      id="graph"
      onclick="return doGraph(); "
      class="col-span-4 btn btn-primary justify-content-end"
    >
      Graph
    </button>
    <button
      id="text"
      onclick="return doText();"
      class="col-span-4 btn btn-primary justify-content-end"
    >
      Text
    </button>
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
