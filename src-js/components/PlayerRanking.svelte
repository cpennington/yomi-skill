<script lang="ts">
    import type { PlayerSummary } from "$lib/types";
    import Grid from "gridjs-svelte";

    export let players: PlayerSummary;

    $: columns = players[0].elo
        ? [
              { name: "Player", id: "player" },
              {
                  name: "Rating",
                  id: "elo",
                  formatter: (value: number) => value.toPrecision(4),
              },
          ]
        : [
              { name: "Player", id: "player" },
              {
                  name: "Rating",
                  id: "glickoR",
                  formatter: (value: number) => value.toPrecision(4),
              },
              {
                  name: "Rating Deviation",
                  id: "glickoRD",
                  formatter: (value: number) => value.toPrecision(3),
              },
          ];
</script>

<Grid data={players} search={true} {columns} pagination={true} sort={true} />

<style global lang="scss">
    @import "https://cdn.jsdelivr.net/npm/gridjs/dist/theme/mermaid.min.css";
</style>
