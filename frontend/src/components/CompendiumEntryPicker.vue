<script setup lang="ts">
import { computed } from "vue";
import type { BuilderEntry } from "../api";

const props = withDefaults(
  defineProps<{
    modelValue?: number;
    items?: BuilderEntry[];
    label: string;
    loading?: boolean;
    disabled?: boolean;
    clearable?: boolean;
    preferredIds?: number[];
  }>(),
  {
    items: () => [],
    loading: false,
    disabled: false,
    clearable: false,
    preferredIds: () => [],
  },
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

const orderedItems = computed(() => {
  const preferred = new Set(props.preferredIds);
  return [...props.items].sort(
    (left, right) => Number(preferred.has(right.id)) - Number(preferred.has(left.id)),
  );
});

function isFirstOther(item: BuilderEntry): boolean {
  const firstOther = orderedItems.value.find(
    (candidate) => !props.preferredIds.includes(candidate.id),
  );
  return Boolean(props.preferredIds.length && firstOther?.id === item.id);
}
</script>

<template>
  <v-autocomplete
    :model-value="modelValue"
    :items="orderedItems"
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
    <template #item="{ props: itemProps, item }">
      <v-list-subheader
        v-if="item.raw.id === orderedItems[0]?.id && preferredIds.length"
      >
        Previously chosen classes
      </v-list-subheader>
      <v-divider v-if="isFirstOther(item.raw)" />
      <v-list-subheader v-if="isFirstOther(item.raw)">
        All enabled classes
      </v-list-subheader>
      <v-list-item
        v-bind="itemProps"
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
