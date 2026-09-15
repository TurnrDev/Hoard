<template>
  <label class="d-grid gap-2">
    <span class="fw-semibold">{{ label }}</span>
    <Select
      :model-value="selectedId"
      :options="orderedItems"
      :option-label="displayTitle"
      option-value="id"
      :loading="loading"
      :disabled="disabled"
      :show-clear="clearable"
      filter
      fluid
      @update:model-value="$emit('update:modelValue', $event ?? undefined)"
    />
  </label>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Select from "primevue/select";
import type { BuilderEntry } from "@/api";

export default defineComponent({
  components: { Select },
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
  computed: {
    orderedItems(): BuilderEntry[] {
      const preferred = new Set(this.preferredIds);

      return [...this.items].sort(
        (left, right) =>
          Number(preferred.has(right.id)) - Number(preferred.has(left.id)) ||
          left.name.localeCompare(right.name),
      );
    },
    selectedId(): number | undefined {
      const selectedId = this.modelValue;

      if (selectedId === undefined) {
        return undefined;
      }

      return (
        this.items.find(
          (item) => item.id === selectedId || item.alias_ids?.includes(selectedId),
        )?.id ?? selectedId
      );
    },
  },
  methods: {
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
