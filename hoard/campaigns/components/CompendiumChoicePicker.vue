<template>
  <label class="d-grid gap-2">
    <span class="fw-semibold">{{ label }}</span>
    <Select
      v-if="!allowCustom && !multiple"
      :model-value="modelValue"
      :options="items"
      :option-label="displayTitle"
      option-value="name"
      :loading="loading"
      :disabled="disabled"
      show-clear
      filter
      fluid
      @update:model-value="$emit('update:modelValue', $event ?? '')"
    />
    <MultiSelect
      v-else-if="!allowCustom"
      :model-value="modelValue"
      :options="items"
      :option-label="displayTitle"
      option-value="name"
      :loading="loading"
      :disabled="disabled"
      :display="chips ? 'chip' : 'comma'"
      filter
      fluid
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <AutoComplete
      v-else
      :model-value="inputValue"
      :suggestions="suggestions"
      :option-label="displayTitle"
      :loading="loading"
      :disabled="disabled"
      :multiple="multiple"
      :show-clear="!multiple"
      :min-length="0"
      complete-on-focus
      dropdown
      dropdown-mode="blank"
      fluid
      @complete="search"
      @update:model-value="updateModelValue"
    />
    <small class="text-body-secondary">{{ hint }}</small>
  </label>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import AutoComplete from "primevue/autocomplete";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";

export type CompendiumChoice = {
  identifier?: string;
  name: string;
  source: string;
  level?: number;
};

export default defineComponent({
  components: { AutoComplete, MultiSelect, Select },
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
    allowCustom: { type: Boolean, default: true },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      query: "",
      inputValue: "" as CompendiumChoice | string | Array<CompendiumChoice | string>,
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
  watch: {
    modelValue: {
      immediate: true,
      deep: true,
      handler() {
        this.syncInputValue();
      },
    },
    items: {
      deep: true,
      handler() {
        this.syncInputValue();
      },
    },
  },
  methods: {
    search(event: { originalEvent: Event; query: string }): void {
      this.query = event.originalEvent.type === "focus" ? "" : event.query;
    },
    displayTitle(item: CompendiumChoice): string {
      return `${item.name} — ${item.source}`;
    },
    choiceName(value: CompendiumChoice | string): string {
      return typeof value === "string" ? value : value.name;
    },
    updateModelValue(
      value: CompendiumChoice | string | Array<CompendiumChoice | string> | null,
    ): void {
      this.inputValue = value ?? (this.multiple ? [] : "");

      if (Array.isArray(value)) {
        this.$emit("update:modelValue", value.map(this.choiceName));
        return;
      }

      this.$emit("update:modelValue", value ? this.choiceName(value) : "");
    },
    choiceValue(name: string): CompendiumChoice | string {
      return this.items.find((item) => item.name === name) ?? name;
    },
    syncInputValue(): void {
      if (Array.isArray(this.modelValue)) {
        this.inputValue = this.modelValue.map(this.choiceValue);
        return;
      }

      this.inputValue = this.choiceValue(this.modelValue);
    },
  },
});
</script>
