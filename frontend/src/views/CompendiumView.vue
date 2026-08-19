<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  createItem,
  deleteItem,
  getCampaign,
  getItems,
  updateItem,
  type Campaign,
  type Item,
} from "../api";
import { itemSummary } from "../itemPicker";

const campaignId = Number(useRoute().params.id);
const campaign = ref<Campaign>();
const items = ref<Item[]>([]);
const query = ref("");
const editorOpen = ref(false);
const editing = ref<Item>();
const name = ref("");
const description = ref("");
const error = ref("");
const notice = ref("");
const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase();
  if (!needle) return items.value;
  return items.value.filter((item) =>
    [
      item.name,
      item.description,
      item.source_system,
      item.equipment.category,
      item.equipment.item_type,
      item.equipment.source_book,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(needle),
  );
});

async function load(): Promise<void> {
  try {
    [campaign.value, items.value] = await Promise.all([
      getCampaign(campaignId),
      getItems(campaignId),
    ]);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load the compendium.";
  }
}
function openEditor(item?: Item): void {
  editing.value = item;
  name.value = item?.name ?? "";
  description.value = item?.description ?? "";
  editorOpen.value = true;
}
async function save(): Promise<void> {
  if (!name.value.trim()) return;
  try {
    if (editing.value)
      await updateItem(campaignId, editing.value.id, {
        name: name.value.trim(),
        description: description.value,
      });
    else await createItem(campaignId, name.value.trim(), description.value);
    notice.value = editing.value ? "Item updated." : "Item created.";
    editorOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to save item.";
  }
}
async function remove(item: Item): Promise<void> {
  try {
    await deleteItem(campaignId, item.id);
    notice.value = "Item deleted.";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to delete item.";
  }
}
onMounted(load);
</script>

<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Campaign library</div>
        <h1>Compendium</h1>
        <p>Browse imported references and campaign-local equipment.</p>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openEditor()"
        >New item</v-btn
      >
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
      >{{ error }}</v-alert
    ><v-alert
      v-if="notice"
      type="success"
      closable
      class="mb-4"
      @click:close="notice = ''"
      >{{ notice }}</v-alert
    >
    <v-text-field
      v-model="query"
      prepend-inner-icon="mdi-magnify"
      label="Search the compendium"
      clearable
    />
    <div class="text-caption mb-3">{{ filtered.length }} matching items</div>
    <v-row
      ><v-col v-for="item in filtered" :key="item.id" cols="12" sm="6" lg="4"
        ><v-card class="h-100"
          ><v-card-title>{{ item.name }}</v-card-title
          ><v-card-subtitle>{{
            itemSummary(item) ||
            (item.is_imported ? "Imported item" : "Campaign custom item")
          }}</v-card-subtitle
          ><v-card-text
            ><p class="item-description">
              {{ item.description || "No description." }}
            </p>
            <v-chip v-if="item.equipment.category" size="small" class="mr-1">{{
              item.equipment.category
            }}</v-chip
            ><v-chip
              v-if="item.equipment.item_type"
              size="small"
              class="mr-1"
              >{{ item.equipment.item_type }}</v-chip
            ><v-chip v-if="item.equipment.rarity" size="small">{{
              item.equipment.rarity
            }}</v-chip></v-card-text
          ><v-card-actions v-if="campaign?.is_game_master && !item.is_imported"
            ><v-btn @click="openEditor(item)">Edit</v-btn
            ><v-btn color="error" @click="remove(item)"
              >Delete</v-btn
            ></v-card-actions
          ></v-card
        ></v-col
      ></v-row
    >
    <v-dialog v-model="editorOpen" max-width="640"
      ><v-card :title="editing ? 'Edit campaign item' : 'Create campaign item'"
        ><v-card-text
          ><v-text-field v-model="name" label="Name" /><v-textarea
            v-model="description"
            label="Description" /></v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="editorOpen = false">Cancel</v-btn
          ><v-btn color="primary" @click="save">Save</v-btn></v-card-actions
        ></v-card
      ></v-dialog
    >
  </v-container>
</template>

<style scoped>
.item-description {
  min-height: 3.2em;
}
</style>
