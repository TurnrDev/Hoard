<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Item } from "../api";
import {
  defaultPickerFilters,
  itemMatchesFilters,
  itemSummary,
  type PickerCandidate,
} from "../itemPicker";

const props = withDefaults(
  defineProps<{
    candidates: PickerCandidate[];
    modelValue?: number;
    label?: string;
    noDataText?: string;
  }>(),
  { label: "Item", noDataText: "No matching items." },
);

const emit = defineEmits<{
  "update:modelValue": [value: number | undefined];
}>();
const open = ref(false);
const detailItem = ref<Item>();
const page = ref(1);
const pageSize = 24;
const filters = ref(defaultPickerFilters());

const selected = computed(() =>
  props.candidates.find((candidate) => candidate.item.id === props.modelValue),
);
const filtered = computed(() =>
  props.candidates.filter(({ item }) =>
    itemMatchesFilters(item, filters.value),
  ),
);
const pageCount = computed(() =>
  Math.max(1, Math.ceil(filtered.value.length / pageSize)),
);
const results = computed(() =>
  filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize),
);
const values = (getter: (item: Item) => string | null): string[] =>
  [
    ...new Set(
      props.candidates
        .map(({ item }) => getter(item))
        .filter((value): value is string => Boolean(value)),
    ),
  ].sort();
const systems = computed(() => values((item) => item.source_system));
const sourceBooks = computed(() =>
  values((item) => item.equipment.source_book),
);
const categories = computed(() => values((item) => item.equipment.category));
const types = computed(() => values((item) => item.equipment.item_type));
const rarities = computed(() => values((item) => item.equipment.rarity));

watch(
  filters,
  () => {
    page.value = 1;
  },
  { deep: true },
);
watch(pageCount, () => {
  if (page.value > pageCount.value) page.value = pageCount.value;
});

function choose(candidate: PickerCandidate): void {
  emit("update:modelValue", candidate.item.id);
  open.value = false;
}

function clear(): void {
  emit("update:modelValue", undefined);
}
function resetFilters(): void {
  filters.value = defaultPickerFilters();
}
function facts(item: Item): string[] {
  return [
    item.equipment.category,
    item.equipment.item_type,
    item.equipment.rarity,
  ].filter((fact): fact is string => Boolean(fact));
}
</script>

<template>
  <div class="item-picker-field mb-4">
    <div class="text-subtitle-2 mb-1">{{ label }}</div>
    <v-btn
      block
      variant="outlined"
      class="justify-start text-none"
      @click="open = true"
    >
      <v-icon start>mdi-package-variant</v-icon>
      <span v-if="selected" class="text-truncate"
        >{{ selected.item.name }}
        <span class="text-medium-emphasis"
          >— {{ itemSummary(selected.item) }}</span
        ></span
      >
      <span v-else class="text-medium-emphasis">Choose an item</span>
      <template #append
        ><v-btn
          v-if="selected"
          icon="mdi-close"
          size="x-small"
          variant="text"
          @click.stop="clear"
      /></template>
    </v-btn>
  </div>

  <v-dialog v-model="open" max-width="1200" scrollable>
    <v-card title="Choose equipment">
      <v-card-text class="pt-0">
        <v-text-field
          v-model="filters.search"
          prepend-inner-icon="mdi-magnify"
          label="Search name, description, source, category, or type"
          clearable
        />
        <v-row dense>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.system"
              :items="systems"
              label="System"
              clearable
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.sourceBook"
              :items="sourceBooks"
              label="Source book"
              clearable
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.category"
              :items="categories"
              label="Category"
              clearable
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.itemType"
              :items="types"
              label="Type"
              clearable
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.rarity"
              :items="rarities"
              label="Rarity"
              clearable
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.magic"
              :items="[
                { title: 'Any magic status', value: 'any' },
                { title: 'Magic only', value: 'yes' },
                { title: 'Non-magic only', value: 'no' },
              ]"
              label="Magic"
          /></v-col>
          <v-col cols="12" sm="6" md="3"
            ><v-select
              v-model="filters.attunement"
              :items="[
                { title: 'Any attunement', value: 'any' },
                { title: 'Attunement required', value: 'yes' },
                { title: 'No attunement', value: 'no' },
              ]"
              label="Attunement"
          /></v-col>
          <v-col cols="6" md="3"
            ><v-text-field
              v-model.number="filters.minCost"
              type="number"
              min="0"
              label="Min cost (gp)"
              clearable
          /></v-col>
          <v-col cols="6" md="3"
            ><v-text-field
              v-model.number="filters.maxCost"
              type="number"
              min="0"
              label="Max cost (gp)"
              clearable
          /></v-col>
          <v-col cols="6" md="3"
            ><v-text-field
              v-model.number="filters.minWeight"
              type="number"
              min="0"
              label="Min weight"
              clearable
          /></v-col>
          <v-col cols="6" md="3"
            ><v-text-field
              v-model.number="filters.maxWeight"
              type="number"
              min="0"
              label="Max weight"
              clearable
          /></v-col>
        </v-row>
        <div class="d-flex align-center justify-space-between mb-3">
          <span class="text-caption">{{ filtered.length }} matching items</span
          ><v-btn size="small" variant="text" @click="resetFilters"
            >Reset filters</v-btn
          >
        </div>
        <v-alert v-if="!results.length" type="info" variant="tonal">{{
          noDataText
        }}</v-alert>
        <v-row v-else dense>
          <v-col
            v-for="candidate in results"
            :key="candidate.item.id"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card
              class="h-100"
              :color="candidate.item.id === modelValue ? 'primary' : undefined"
              @click="choose(candidate)"
            >
              <v-card-title class="d-flex align-start"
                ><span class="text-wrap">{{ candidate.item.name }}</span
                ><v-spacer /><v-chip
                  v-if="candidate.quantity !== undefined"
                  size="small"
                  >{{ candidate.quantity }} held</v-chip
                ></v-card-title
              >
              <v-card-subtitle>{{
                itemSummary(candidate.item) || "No catalogue facts recorded"
              }}</v-card-subtitle>
              <v-card-text
                ><div class="mb-2">
                  {{ candidate.item.description || "No description." }}
                </div>
                <v-chip
                  v-for="fact in facts(candidate.item)"
                  :key="fact"
                  size="x-small"
                  class="mr-1"
                  >{{ fact }}</v-chip
                ><v-btn
                  size="x-small"
                  class="float-right"
                  variant="text"
                  @click.stop="detailItem = candidate.item"
                  >Details</v-btn
                ></v-card-text
              >
            </v-card>
          </v-col>
        </v-row>
        <v-pagination
          v-if="pageCount > 1"
          v-model="page"
          :length="pageCount"
          class="mt-4"
        />
      </v-card-text>
      <v-card-actions
        ><v-spacer /><v-btn @click="open = false">Cancel</v-btn></v-card-actions
      >
    </v-card>
  </v-dialog>

  <v-dialog
    :model-value="Boolean(detailItem)"
    max-width="650"
    @update:model-value="
      (value) => {
        if (!value) detailItem = undefined;
      }
    "
    ><v-card v-if="detailItem" :title="detailItem.name"
      ><v-card-subtitle>{{ itemSummary(detailItem) }}</v-card-subtitle
      ><v-card-text
        ><p class="mb-4">{{ detailItem.description || "No description." }}</p>
        <v-list density="compact"
          ><v-list-item
            v-if="detailItem.equipment.category"
            title="Category"
            :subtitle="detailItem.equipment.category" /><v-list-item
            v-if="detailItem.equipment.item_type"
            title="Type"
            :subtitle="detailItem.equipment.item_type" /><v-list-item
            v-if="detailItem.equipment.rarity"
            title="Rarity"
            :subtitle="detailItem.equipment.rarity" /><v-list-item
            v-if="detailItem.equipment.is_magic !== null"
            title="Magic"
            :subtitle="
              detailItem.equipment.is_magic ? 'Yes' : 'No'
            " /><v-list-item
            v-if="detailItem.equipment.requires_attunement !== null"
            title="Attunement"
            :subtitle="
              detailItem.equipment.requires_attunement
                ? 'Required'
                : 'Not required'
            " /><v-list-item
            v-if="detailItem.created_by_username"
            title="Created by"
            :subtitle="detailItem.created_by_username" /></v-list></v-card-text
      ><v-card-actions
        ><v-spacer /><v-btn @click="detailItem = undefined"
          >Close</v-btn
        ></v-card-actions
      ></v-card
    ></v-dialog
  >
</template>
