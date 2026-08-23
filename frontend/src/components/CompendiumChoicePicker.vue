<script setup lang="ts">
export type CompendiumChoice = {
  identifier?: string;
  name: string;
  source: string;
  level?: number;
};

withDefaults(
  defineProps<{
    modelValue?: string | string[];
    items?: CompendiumChoice[];
    label: string;
    hint?: string;
    loading?: boolean;
    disabled?: boolean;
    multiple?: boolean;
    chips?: boolean;
  }>(),
  {
    modelValue: "",
    items: () => [],
    hint: "Compendium suggestion or custom override",
    loading: false,
    disabled: false,
    multiple: false,
    chips: false,
  },
);

defineEmits<{ "update:modelValue": [value: string | string[]] }>();

function choiceName(value: unknown): string {
  return typeof value === "object" && value !== null && "name" in value
    ? String(value.name)
    : String(value ?? "");
}

function choiceSource(value: unknown): string {
  return typeof value === "object" && value !== null && "source" in value
    ? String(value.source)
    : "Custom override";
}

function displayTitle(item: CompendiumChoice): string {
  return `${item.name} — ${item.source}`;
}
</script>

<template>
  <v-combobox
    :model-value="modelValue"
    :items="items"
    :item-title="displayTitle"
    item-value="name"
    :label="label"
    :hint="hint"
    persistent-hint
    :loading="loading"
    :disabled="disabled"
    :multiple="multiple"
    :chips="chips"
    :return-object="false"
    no-data-text="No Compendium suggestions match. Enter a custom override if allowed."
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #item="{ props, item }">
      <v-list-item
        v-bind="props"
        :title="choiceName(item.raw)"
        :subtitle="choiceSource(item.raw)"
      />
    </template>
    <template #selection="{ item }">
      <v-chip v-if="multiple">
        {{ choiceName(item.raw) }}
        <span class="text-medium-emphasis ml-1">· {{ choiceSource(item.raw) }}</span>
      </v-chip>
      <template v-else>
        <span>{{ choiceName(item.raw) }}</span>
        <span class="text-medium-emphasis ml-2">— {{ choiceSource(item.raw) }}</span>
      </template>
    </template>
  </v-combobox>
</template>
