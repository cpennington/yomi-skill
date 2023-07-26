<script>
  import InputButton from "./InputButton.svelte";
  export let againstElo = "self";
  export let againstCharElo = "self";
</script>

<div id="against-cfg" class="grid grid-cols-12 p-1">
  <label for="against-elo" class="col-span-2 p-1 text-sm">Against Elo:</label>

  <div
    id="against-elo"
    class="grid grid-cols-7 col-span-4 rounded-md overflow-clip"
    data-toggle="buttons"
  >
    <InputButton
      value="self"
      label="Own"
      bind:group={againstElo}
      name="againstElo"
      checked
    />
    <InputButton
      value={0}
      label="0"
      bind:group={againstElo}
      name="againstElo"
    />
    <InputButton
      value={1}
      label="25%"
      bind:group={againstElo}
      name="againstElo"
    />
    <InputButton
      value={2}
      label="50%"
      bind:group={againstElo}
      name="againstElo"
    />
    <InputButton
      value={3}
      label="75%"
      bind:group={againstElo}
      name="againstElo"
    />
    <InputButton
      value={4}
      label="95%"
      bind:group={againstElo}
      name="againstElo"
    />
    <InputButton
      value={5}
      label="Max"
      bind:group={againstElo}
      name="againstElo"
    />
  </div>
  <label for="against-skill" class="col-span-2 p-1 text-sm text-right"
    >Against Char Skill:</label
  >

  <div
    id="against-skill"
    class="grid grid-cols-7 col-span-4 rounded-md overflow-clip"
    data-toggle="buttons"
  >
    <InputButton
      value="self"
      label="Own"
      bind:group={againstCharElo}
      name="againstCharElo"
      checked
    />
    <InputButton
      value={0}
      label="5%"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
    <InputButton
      value={1}
      label="25%"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
    <InputButton
      value={2}
      label="50%"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
    <InputButton
      value={3}
      label="75%"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
    <InputButton
      value={4}
      label="95%"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
    <InputButton
      value={5}
      label="Max"
      bind:group={againstCharElo}
      name="againstCharElo"
    />
  </div>
</div>
