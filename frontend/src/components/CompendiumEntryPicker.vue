<template>
  <label class="d-grid gap-2">
    <span class="fw-semibold">{{ label }}</span>
    <AutoComplete
      :model-value="modelValue"
      :suggestions="suggestions"
      :option-label="displayTitle"
      option-value="id"
      :loading="loading"
      :disabled="disabled"
      :show-clear="clearable"
      dropdown
      fluid
      @complete="search"
      @update:model-value="$emit('update:modelValue', $event ?? undefined)"
    />
  </label>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import AutoComplete from "primevue/autocomplete";
import type { BuilderEntry } from "../api";

export default defineComponent({
  components: { AutoComplete },
  props: {
    modelValue: { type: Number, default: undefined },
    items: {
      type: Array as PropType<BuilderEntry[]>,
      default: () => [],
    },
    label: { type: String, required: true },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    clearable: { type: Boolean, default: false },
    preferredIds: {
      type: Array as PropType<number[]>,
      default: () => [],
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      query: "",
    };
  },
  computed: {
    orderedItems(): BuilderEntry[] {
      const preferred = new Set(this.preferredIds);

      return [...this.items].sort(
        (left, right) =>
          Number(preferred.has(right.id)) - Number(preferred.has(left.id)) ||
          left.name.localeCompare(right.name),
      );
    },
    suggestions(): BuilderEntry[] {
      const normalizedQuery = this.query.trim().toLowerCase();

      if (!normalizedQuery) {
        return this.orderedItems;
      }

      return this.orderedItems.filter((item) =>
        this.displayTitle(item).toLowerCase().includes(normalizedQuery),
      );
    },
  },
  methods: {
    search(event: { query: string }): void {
      this.query = event.query;
    },
    displayTitle(item: BuilderEntry): string {
      return `${item.name} — ${this.sourceTags(item).join(" · ")}`;
    },
    sourceTags(item: BuilderEntry): string[] {
      return [
        item.source,
        item.source_book,
        item.repository_identifier === "default" ? "" : item.repository,
      ].filter(
        (value, index, values): value is string =>
          Boolean(value) && values.indexOf(value) === index,
      );
    },
  },
});
</script>
