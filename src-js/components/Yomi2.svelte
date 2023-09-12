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

  const game = "yomi2";
  export let matchupData: MatchupData;
  export let characters: CharacterPlayCounts;
  export let scales: Scales;
  export let aggregateSkill: AggregatePlayerSkill;
  export let players: PlayerSummary;
  export let gemEffects: GemEffects;

  const CHAR_MAP = { A: "Grave", G: "Valerie" };
  const GEM_MAP = { a: "Red", b: "Green" };
  type CharKey = keyof typeof CHAR_MAP;
  type GemKey = keyof typeof GEM_MAP;
  type CharGem = `${CharKey}${GemKey}`;

  let againstRating: "self" | number = "self";
  let againstCharRating: "self" | number = "self";

  let player = "";
  let opponent = "";

  function parseCharGem(charGem: CharGem) {
    const char = CHAR_MAP[charGem[0] as CharKey];
    const gem = GEM_MAP[charGem[1] as GemKey];
  }

  function toMillis(seconds: number): number {
    return seconds * 1000;
  }

  async function processLogFile(fileHandle) {
    console.log({ fileHandle });
    const file = await fileHandle.getFile();
    const startTime =
      /\[(?<threadId>.) (?<timestamp>[^\]]*)\] Yomi2 Start: (?<version>.*) at localtime (?<localTime>[^,]*), UTC (?<utcTime>.*)/;

    const matchComplete =
      /\[(?<threadId>.) (?<timestamp>[^\]]*)\] (?<gameType>[^ ]*) Game over: (?<p0Location>Remote|Local) P0 \[(?<p0Name>[^\]]*)\] (?<p0Char>[^-]*)-(?<p0Gem>[^ ]*) (?<result>[^ ]*) vs (?<p1Location>Remote|Local) P1 \[(?<p1Name>[^\]]*)\] (?<p1Char>[^-]*)-(?<p1Gem>\S*)/;

    let zeroTime = null;
    for (const line of (await file.text()).split("\n") as string[]) {
      const startTimeMatch = startTime.exec(line);
      const matchCompleteMatch = matchComplete.exec(line);

      if (startTimeMatch) {
        const startMillis = new Date(
          startTimeMatch.groups!.utcTime.replace(" ", "T")
        ).valueOf();
        const offsetMillis = toMillis(
          new Number(startTimeMatch.groups!.timestamp).valueOf()
        );
        zeroTime = startMillis - offsetMillis;
      }
      if (matchCompleteMatch) {
        const message = {
          ...matchCompleteMatch.groups,
          realTime: new Date(
            toMillis(
              new Number(matchCompleteMatch.groups!.timestamp).valueOf()
            ) + zeroTime!
          ),
          zeroTime,
          rawLine: line.trim(),
        };
        const response = fetch(
          "https://yomi-2-results-uploader.vengefulpickle.com",
          {
            body: JSON.stringify(message),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          }
        );
        console.log(response);
      }
    }
  }

  async function watchLogs(evt) {
    const handle = await window.showDirectoryPicker({});
    const playerLog = handle.getFileHandle("Player.log");
    const oldPlayerLog = handle.getFileHandle("Player-prev.log");
    processLogFile(await playerLog);
    processLogFile(await oldPlayerLog);
  }
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

  <div class="row col-12">
    <p class="col-12 mt-4">
      If you'd like to improve the matchup chart, report your matches with the
      <a href="https://forms.gle/DRMW4MAxB3dWZS1K9">Yomi 2 Match Report form</a
      >!
    </p>
    <button on:click={watchLogs}>Upload!</button>
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

<PlayerRanking {players} />
