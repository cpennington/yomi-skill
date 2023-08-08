<script lang="ts":>
  import InputButton from "./InputButton.svelte";
  export let againstRating: "self" | number = "self";
  export let againstCharRating: "self" | number = "self";
</script>

<div id="against-cfg" class="grid grid-cols-12 p-1">
  <label for="against-rating" class="col-span-2 p-1 text-sm"
    >Against Rating:</label
  >

  <div
    id="against-rating"
    class="grid grid-cols-7 col-span-4 rounded-md overflow-clip"
    data-toggle="buttons"
  >
    <InputButton
      value="self"
      label="Own"
      bind:group={againstRating}
      name="againstRating"
      checked
    />
    <InputButton
      value={0}
      label="0"
      bind:group={againstRating}
      name="againstRating"
    />
    <InputButton
      value={1}
      label="25%"
      bind:group={againstRating}
      name="againstRating"
    />
    <InputButton
      value={2}
      label="50%"
      bind:group={againstRating}
      name="againstRating"
    />
    <InputButton
      value={3}
      label="75%"
      bind:group={againstRating}
      name="againstRating"
    />
    <InputButton
      value={4}
      label="95%"
      bind:group={againstRating}
      name="againstRating"
    />
    <InputButton
      value={5}
      label="Max"
      bind:group={againstRating}
      name="againstRating"
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
      bind:group={againstCharRating}
      name="againstCharRating"
      checked
    />
    <InputButton
      value={0}
      label="5%"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
    <InputButton
      value={1}
      label="25%"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
    <InputButton
      value={2}
      label="50%"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
    <InputButton
      value={3}
      label="75%"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
    <InputButton
      value={4}
      label="95%"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
    <InputButton
      value={5}
      label="Max"
      bind:group={againstCharRating}
      name="againstCharRating"
    />
  </div>
</div>
