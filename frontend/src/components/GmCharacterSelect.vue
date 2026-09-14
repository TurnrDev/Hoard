<template>
  <label class="d-grid gap-2">
    <span class="fw-semibold">Character</span>
    <Select
      v-model="selectedId"
      :options="options"
      option-label="label"
      option-value="value"
      fluid
    />
  </label>
</template>

<script lang="ts">
import Select from "primevue/select";
import { defineComponent, type PropType } from "vue";
import type { Character } from "../api";

export default defineComponent({
  components: { Select },
  props: { characters: { type: Array as PropType<Character[]>, required: true } },
  emits: ["selected"],
  data() {
    return { selectedId: undefined as number | undefined };
  },
  computed: {
    options(): Array<{ label: string; value: number }> {
      return this.characters.map((character) => ({
        label: character.name,
        value: character.id,
      }));
    },
  },
  watch: {
    characters: {
      immediate: true,
      handler(characters: Character[]): void {
        if (!characters.some((character) => character.id === this.selectedId)) {
          this.selectedId = characters[0]?.id;
        }
        this.$emit("selected", this.selectedId);
      },
    },
    selectedId(characterId: number | undefined): void {
      this.$emit("selected", characterId);
    },
  },
});
</script>
