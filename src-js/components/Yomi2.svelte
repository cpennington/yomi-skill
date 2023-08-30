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

  function processLogFile(fileHandle) {
    const file = fileHandle.getFile();
    const modifiedTime = file.lastModified;

    const connectedAndAuthenticated =
      /YServerConnection.ConnectedAndAuthenticated as (?<p1Name>.*)/;
    const startLiveOnlineGame =
      /StartLiveOnlineGame as (?<whichPlayer>.*) (?<p1Char>[^:]*):(?<p1Gem>[^ ]*) vs (?<p2Name>interruptvector) (?<p2Char>[^:]*):(?<p2Gem>[^,*]), asRejoin (?<rejoin>[^,]*), isFriendMatch (?<friendMatch>.*)/;
    const timestamp = /$\[(?<threadId>.) (?<timestamp>[^\]]*)\]/;
    const charGemChoice =
      /RememberCharGemChoice: (?<char>[^ ]*) (?<gem>[^ ]*), forOpp (?<forOpp>[^,]*),/;
    const matchCommand =
      /< Server: \[(?<matchCommand>startgame|want_rematch|endmatch|want_changechargemandrematch:(?<newCharGem>[^\]]*))\]/;
  }

  async function watchLogs(evt) {
    const handle = await window.showDirectoryPicker({});
    const playerLog = handle.getFileHandle("Player.log");
    const oldPlayerLog = handle.getFileHandle("Player-prev.log");
    console.log({ handle });
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
