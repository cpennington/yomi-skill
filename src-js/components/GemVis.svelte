<script lang="ts">
  import type { CharacterPlayCounts, GemEffects } from "$lib/types";
  import { getContext, onMount } from "svelte";
  import embed from "vega-embed";

  async function renderCharSkill(
    characters: CharacterPlayCounts,
    gemEffects: GemEffects
  ) {
    const playedCharacters = characters
      .filter((char) => char.gamesRecorded > 0)
      .map((char) => char.character);
    var data = Object.entries(gemEffects.with_gem)
      .filter(([character, _]) => playedCharacters.includes(character))
      .flatMap(([character, gems]) =>
        Object.entries(gems).map(([gem, effect]) => ({
          effect: "with",
          gem,
          character,
          ...effect,
        }))
      )
      .concat(
        Object.entries(gemEffects.against_gem).flatMap(([gem, characters]) =>
          Object.entries(characters)
            .filter(([character, _]) => playedCharacters.includes(character))
            .map(([character, effect]) => ({
              effect: "against",
              gem,
              character,
              ...effect,
            }))
        )
      );
    var spec = {
      data: { values: data },
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      facet: {
        row: { field: "effect", type: "nominal" },
        column: { field: "character", type: "nominal" },
      },
      spec: {
        width: 50,
        height: 40,
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
              yError: { field: "std" },
              x: { field: "gem", type: "nominal" },
              fill: {
                field: "gem",
                type: "nominal",
                scale: {
                  domain: [
                    "red",
                    "blue",
                    "green",
                    "purple",
                    "white",
                    "black",
                    "diamond",
                    "orange",
                  ],
                  range: [
                    "rgb(255, 0, 0)",
                    "rgb(0, 0, 255)",
                    "rgb(0, 255, 0)",
                    "rgb(255, 0, 255)",
                    "rgb(200, 200, 200)",
                    "rgb(0, 0, 0)",
                    "rgb(154, 184, 188)",
                    "rgb(255, 181, 10)",
                  ],
                },
              },
            },
          },
          {
            mark: {
              type: "point",
              tooltip: { content: "data" },
            },
            encoding: {
              color: {
                field: "gem",
                type: "nominal",
                scale: {
                  domain: ["red", "blue", "green", "purple", "white", "black"],
                  range: [
                    "rgb(255, 0, 0)",
                    "rgb(0, 0, 255)",
                    "rgb(0, 255, 0)",
                    "rgb(255, 0, 255)",
                    "rgb(200, 200, 200)",
                    "rgb(0, 0, 0)",
                  ],
                },
              },
              y: { field: "mean", type: "quantitative" },
              x: { field: "gem", type: "nominal" },
            },
          },
        ],
        config: { mark: { filled: true } },
      },
    };
    embed("#gem-effect-vis", spec);
  }

  export let gemEffects: GemEffects;
  export let characters: CharacterPlayCounts;

  $: mounted && renderCharSkill(characters, gemEffects);
  let mounted = false;
  onMount(() => {
    mounted = true;
  });
</script>

<div id="gem-effect-vis" />
