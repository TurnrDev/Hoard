<script setup lang="ts">
import type { BuilderEntry } from "../api";

withDefaults(
  defineProps<{
    modelValue?: number;
    items?: BuilderEntry[];
    label: string;
    loading?: boolean;
    disabled?: boolean;
    clearable?: boolean;
  }>(),
  { items: () => [], loading: false, disabled: false, clearable: false },
);

defineEmits<{ "update:modelValue": [value: number | undefined] }>();

function displayTitle(item: BuilderEntry): string {
  return `${item.name} — ${sourceTags(item).join(" · ")}`;
}

function sourceTags(item: BuilderEntry): string[] {
  return [
    item.source,
    item.source_book,
    item.repository_identifier === "default" ? "" : item.repository,
  ].filter(
    (value, index, values): value is string =>
      Boolean(value) && values.indexOf(value) === index,
  );
}
</script>

<template>
  <v-autocomplete
    :model-value="modelValue"
    :items="items"
    :item-title="displayTitle"
    item-value="id"
    :label="label"
    :loading="loading"
    :disabled="disabled"
    :clearable="clearable"
    no-data-text="No enabled Compendium entries match your search."
    auto-select-first
    @update:model-value="$emit('update:modelValue', $event ?? undefined)"
  >
    <template #item="{ props, item }">
      <v-list-item
        v-bind="props"
        :title="item.raw.name"
      >
        <template #subtitle>
          <v-chip
            v-for="tag in sourceTags(item.raw)"
            :key="tag"
            size="x-small"
            class="mr-1 mt-1"
          >
            {{ tag }}
          </v-chip>
        </template>
      </v-list-item>
    </template>
    <template #selection="{ item }">
      <span>{{ item.raw.name }}</span>
      <v-chip
        v-for="tag in sourceTags(item.raw)"
        :key="tag"
        size="x-small"
        class="ml-1"
      >
        {{ tag }}
      </v-chip>
    </template>
  </v-autocomplete>
</template>
