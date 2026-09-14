<template>
  <label class="d-grid gap-2">
    <span class="fw-semibold">{{ label }}</span>
    <AutoComplete
      :model-value="modelValue"
      :suggestions="suggestions"
      :option-label="displayTitle"
      option-value="name"
      :loading="loading"
      :disabled="disabled"
      :multiple="multiple"
      :show-clear="!multiple"
      dropdown
      fluid
      @complete="search"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <small class="text-body-secondary">{{ hint }}</small>
  </label>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import AutoComplete from "primevue/autocomplete";

export type CompendiumChoice = {
  identifier?: string;
  name: string;
  source: string;
  level?: number;
};

export default defineComponent({
  components: { AutoComplete },
  props: {
    modelValue: {
      type: [String, Array] as PropType<string | string[]>,
      default: "",
    },
    items: {
      type: Array as PropType<CompendiumChoice[]>,
      default: () => [],
    },
    label: { type: String, required: true },
    hint: {
      type: String,
      default: "Compendium suggestion or custom override",
    },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    multiple: { type: Boolean, default: false },
    chips: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      query: "",
    };
  },
  computed: {
    suggestions(): CompendiumChoice[] {
      const normalizedQuery = this.query.trim().toLowerCase();

      if (!normalizedQuery) {
        return this.items;
      }

      return this.items.filter((item) =>
        this.displayTitle(item).toLowerCase().includes(normalizedQuery),
      );
    },
  },
  methods: {
    search(event: { query: string }): void {
      this.query = event.query;
    },
    displayTitle(item: CompendiumChoice): string {
      return `${item.name} — ${item.source}`;
    },
  },
});
</script>
