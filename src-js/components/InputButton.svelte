<script lang="ts">
  export let name: string;
  export let value;
  export let label: string = value;
  export let group;
  export let checked = false;
</script>

<label class="flex flex-col text-center">
  <input
    type="radio"
    {name}
    autocomplete="off"
    {value}
    class="hidden peer"
    bind:group
    {checked}
  />
  <div
    class="p-1 bg-slate-600 text-inherit peer-checked:bg-slate-800 text-slate-50"
  >
    {label}
  </div>
</label>
