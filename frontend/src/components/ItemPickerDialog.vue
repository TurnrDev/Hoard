<template>
  <div :class="['item-picker-field', { 'mb-3': !compact }]">
    <label class="d-block fw-semibold mb-1">{{ label }}</label>
    <div class="d-flex align-items-center gap-2">
      <Button
        outlined
        class="item-picker-field__trigger flex-grow-1 justify-content-start"
        :disabled="disabled || loading"
        :loading="loading"
        @click="show"
      >
        <span
          class="mdi mdi-package-variant"
          aria-hidden="true"
        />
        <span
          v-if="selected"
          class="text-truncate"
        >
          {{ selected.item.name }}
          <span class="text-body-secondary">— {{ itemSummary(selected.item) }}</span>
        </span>
        <span
          v-else
          class="text-body-secondary"
        >
          Choose an item
        </span>
      </Button>
      <Button
        v-if="selected"
        icon="mdi mdi-close"
        size="small"
        text
        :aria-label="`Clear selected item: ${selected.item.name}`"
        @click="clear"
      />
    </div>
  </div>

  <Dialog
    v-model:visible="open"
    modal
    :style="{ width: 'min(75rem, calc(100vw - 2rem))' }"
  >
    <section
      class="item-picker-dialog"
      :aria-labelledby="'item-picker-title'"
    >
      <header>
        <h2 id="item-picker-title">{{ title }}</h2>
      </header>
      <ProgressBar
        v-if="loading"
        indeterminate
      />
      <div class="d-grid gap-3">
        <label
          class="d-block fw-semibold mb-1"
          for="item-picker-search"
        >
          Search name, description, source, category, or type
        </label>
        <InputText
          id="item-picker-search"
          v-model="filters.search"
          fluid
        />
        <fieldset class="item-picker-dialog__filters">
          <legend>Filter equipment</legend>
          <label>
            System
            <Select
              v-model="filters.system"
              :options="systems"
              show-clear
            />
          </label>
          <label>
            Source book
            <Select
              v-model="filters.sourceBook"
              :options="sourceBooks"
              show-clear
            />
          </label>
          <label>
            Category
            <Select
              v-model="filters.category"
              :options="categories"
              show-clear
            />
          </label>
          <label>
            Type
            <Select
              v-model="filters.itemType"
              :options="types"
              show-clear
            />
          </label>
          <label>
            Rarity
            <Select
              v-model="filters.rarity"
              :options="rarities"
              show-clear
            />
          </label>
          <label>
            Magic
            <Select
              v-model="filters.magic"
              :options="[
                { title: 'Any magic status', value: 'any' },
                { title: 'Magic only', value: 'yes' },
                { title: 'Non-magic only', value: 'no' },
              ]"
              option-label="title"
              option-value="value"
            />
          </label>
          <label>
            Attunement
            <Select
              v-model="filters.attunement"
              :options="[
                { title: 'Any attunement', value: 'any' },
                { title: 'Attunement required', value: 'yes' },
                { title: 'No attunement', value: 'no' },
              ]"
              option-label="title"
              option-value="value"
            />
          </label>
          <label>
            Min cost (gp)
            <InputNumber
              v-model.number="filters.minCost"
              :min="0"
              :step="0.01"
              :precision="2"
              show-buttons
            />
          </label>
          <label>
            Max cost (gp)
            <InputNumber
              v-model.number="filters.maxCost"
              :min="0"
              :step="0.01"
              :precision="2"
              show-buttons
            />
          </label>
          <label>
            Min weight
            <InputNumber
              v-model.number="filters.minWeight"
              :min="0"
              :step="0.001"
              :precision="3"
              show-buttons
            />
          </label>
          <label>
            Max weight
            <InputNumber
              v-model.number="filters.maxWeight"
              :min="0"
              :step="0.001"
              :precision="3"
              show-buttons
            />
          </label>
        </fieldset>
        <div class="d-flex align-items-center justify-content-between gap-2">
          <span>{{ filtered.length }} matching items</span>
          <Button
            size="small"
            text
            @click="resetFilters"
          >
            Reset filters
          </Button>
        </div>
        <Message
          v-if="!results.length"
          severity="info"
        >
          {{ noDataText }}
        </Message>
        <ul
          v-else
          class="item-picker-dialog__results list-unstyled m-0 p-0"
        >
          <li
            v-for="candidate in results"
            :key="candidate.item.id"
          >
            <article
              :class="[
                'item-picker-dialog__result border rounded-3 d-grid gap-3 h-100 p-3',
                {
                  'item-picker-dialog__result--selected':
                    candidate.item.id === modelValue,
                },
              ]"
              tabindex="0"
              role="button"
              :aria-pressed="candidate.item.id === modelValue"
              @click="choose(candidate)"
              @keydown.enter="choose(candidate)"
              @keydown.space.prevent="choose(candidate)"
            >
              <header class="d-flex align-items-center justify-content-between gap-2">
                <h3 class="mb-0">{{ candidate.item.name }}</h3>
                <Chip
                  v-if="candidate.quantity !== undefined"
                  size="small"
                >
                  {{ candidate.quantity }} held
                </Chip>
              </header>
              <p class="mb-0">
                {{ itemSummary(candidate.item) || "No catalogue facts recorded" }}
              </p>
              <div class="d-flex align-items-center justify-content-between gap-2">
                <p class="mb-0">
                  {{ candidate.item.description || "No description." }}
                </p>
                <Chip
                  v-for="fact in facts(candidate.item)"
                  :key="fact"
                  size="x-small"
                  class="me-1"
                >
                  {{ fact }}
                </Chip>
                <Button
                  size="x-small"
                  text
                  @click.stop="detailItem = candidate.item"
                >
                  Details
                </Button>
              </div>
            </article>
          </li>
        </ul>
        <Paginator
          v-if="pageCount > 1"
          :first="(page - 1) * 24"
          :rows="24"
          :total-records="filtered.length"
          @page="page = $event.page + 1"
        />
      </div>
      <footer>
        <span />
        <Button @click="open = false">Cancel</Button>
      </footer>
    </section>
  </Dialog>

  <Dialog
    :visible="Boolean(detailItem)"
    modal
    :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    @update:visible="
      (value: boolean) => {
        if (!value) {
          detailItem = undefined;
        }
      }
    "
  >
    <section
      v-if="detailItem"
      :aria-labelledby="'item-detail-title'"
    >
      <h2
        id="item-detail-title"
        class="h3"
      >
        {{ detailItem.name }}
      </h2>
      <p class="text-body-secondary">{{ itemSummary(detailItem) }}</p>
      <p>{{ detailItem.description || "No description." }}</p>
      <dl class="row mb-3">
        <template v-if="detailItem.equipment.category">
          <dt class="col-sm-4">Category</dt>
          <dd class="col-sm-8">
            {{ displayIdentifier(detailItem.equipment.category) }}
          </dd>
        </template>
        <template v-if="detailItem.equipment.item_type">
          <dt class="col-sm-4">Type</dt>
          <dd class="col-sm-8">
            {{ displayIdentifier(detailItem.equipment.item_type) }}
          </dd>
        </template>
        <template v-if="detailItem.equipment.rarity">
          <dt class="col-sm-4">Rarity</dt>
          <dd class="col-sm-8">{{ displayIdentifier(detailItem.equipment.rarity) }}</dd>
        </template>
        <template v-if="detailItem.equipment.is_magic !== null">
          <dt class="col-sm-4">Magic</dt>
          <dd class="col-sm-8">{{ detailItem.equipment.is_magic ? "Yes" : "No" }}</dd>
        </template>
        <template v-if="detailItem.equipment.requires_attunement !== null">
          <dt class="col-sm-4">Attunement</dt>
          <dd class="col-sm-8">
            {{ detailItem.equipment.requires_attunement ? "Required" : "Not required" }}
          </dd>
        </template>
        <template v-if="detailItem.created_by_username">
          <dt class="col-sm-4">Created by</dt>
          <dd class="col-sm-8">{{ detailItem.created_by_username }}</dd>
        </template>
      </dl>
      <footer class="d-flex justify-content-end">
        <Button
          label="Close"
          @click="detailItem = undefined"
        />
      </footer>
    </section>
  </Dialog>
</template>

<script lang="ts">
import Button from "primevue/button";
import Chip from "primevue/chip";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Paginator from "primevue/paginator";
import ProgressBar from "primevue/progressbar";
import Select from "primevue/select";
import { defineComponent, type PropType } from "vue";
import type { Item } from "../api";
import {
  defaultPickerFilters,
  itemMatchesFilters,
  itemSummary,
  type PickerCandidate,
} from "../itemPicker";
import { displayIdentifier } from "../display";

const pageSize = 24;
export default defineComponent({
  components: {
    Button,
    Chip,
    Dialog,
    InputNumber,
    InputText,
    Message,
    Paginator,
    ProgressBar,
    Select,
  },
  props: {
    candidates: { type: Array as PropType<PickerCandidate[]>, required: true },
    modelValue: { type: Number, default: undefined },
    label: { type: String, default: "Item" },
    noDataText: { type: String, default: "No matching items." },
    title: { type: String, default: "Choose equipment" },
    initialSearch: { type: String, default: "" },
    initialCategory: { type: String, default: "" },
    compact: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      open: false,
      detailItem: undefined as Item | undefined,
      page: 1,
      filters: this.initialFilters(),
    };
  },
  computed: {
    selected(): PickerCandidate | undefined {
      return this.candidates.find((candidate) => candidate.item.id === this.modelValue);
    },
    filtered(): PickerCandidate[] {
      return this.candidates.filter(({ item }) =>
        itemMatchesFilters(item, this.filters),
      );
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.filtered.length / pageSize));
    },
    results(): PickerCandidate[] {
      return this.filtered.slice((this.page - 1) * pageSize, this.page * pageSize);
    },
    systems(): string[] {
      return this.values((item) => item.source_system);
    },
    sourceBooks(): string[] {
      return this.values((item) => item.equipment.source_book);
    },
    categories(): string[] {
      return this.values((item) => item.equipment.category);
    },
    types(): string[] {
      return this.values((item) => item.equipment.item_type);
    },
    rarities(): string[] {
      return this.values((item) => item.equipment.rarity);
    },
  },
  watch: {
    filters: {
      deep: true,
      handler(): void {
        this.page = 1;
      },
    },
    pageCount(): void {
      if (this.page > this.pageCount) {
        this.page = this.pageCount;
      }
    },
  },
  methods: {
    itemSummary,
    displayIdentifier,
    initialFilters() {
      const value = defaultPickerFilters();
      value.search = this.initialSearch;
      value.category = this.initialCategory || null;
      return value;
    },
    values(getter: (item: Item) => string | null): string[] {
      return [
        ...new Set(
          this.candidates
            .map(({ item }) => getter(item))
            .filter((value): value is string => Boolean(value)),
        ),
      ].sort();
    },
    choose(candidate: PickerCandidate): void {
      this.$emit("update:modelValue", candidate.item.id);
      this.open = false;
    },
    show(): void {
      this.filters = this.initialFilters();
      this.open = true;
    },
    clear(): void {
      this.$emit("update:modelValue", undefined);
    },
    resetFilters(): void {
      this.filters = defaultPickerFilters();
    },
    facts(item: Item): string[] {
      return [
        item.source_system,
        item.equipment.source_book,
        item.equipment.category,
        item.equipment.item_type,
        item.equipment.rarity,
      ].filter(
        (fact, index, values): fact is string =>
          Boolean(fact) && values.indexOf(fact) === index,
      );
    },
  },
});
</script>

<style scoped>
.item-picker-field__trigger {
  min-width: 0;
}

.item-picker-dialog__filters {
  border: 0;
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
}

.item-picker-dialog__filters legend {
  font-weight: 600;
  grid-column: 1 / -1;
}

.item-picker-dialog__results {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
}

.item-picker-dialog__result {
  cursor: pointer;
}

.item-picker-dialog__result--selected {
  border-color: var(--hoard-accent);
}
</style>
