<script setup lang="ts">
import { computed, ref } from "vue"
import { useCampaign } from "@/stores/campaign"
import { formatGold } from "@/lib/money"
import type { Item, ItemCategory, ItemRarity } from "@/types"

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  "update:modelValue": [boolean]
  pick: [{ item: Item; qty: number }]
}>()

const store = useCampaign()

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
})

const tab = ref<"library" | "create">("library")
const search = ref("")
const categoryFilter = ref<ItemCategory | "all">("all")

const CATEGORIES: (ItemCategory | "all")[] = [
  "all", "weapon", "armor", "consumable", "gear", "treasure", "wondrous", "tool",
]
const RARITIES: ItemRarity[] = ["common", "uncommon", "rare", "very rare", "legendary"]

const rarityColor: Record<ItemRarity, string> = {
  common: "#94a3b8",
  uncommon: "#34d399",
  rare: "#38bdf8",
  "very rare": "#a78bfa",
  legendary: "#fbbf24",
}

const results = computed(() => {
  const q = search.value.trim().toLowerCase()
  return store.campaign.itemLibrary.filter((i) => {
    if (categoryFilter.value !== "all" && i.category !== categoryFilter.value) return false
    if (!q) return true
    return i.name.toLowerCase().includes(q) || i.tags?.some((t) => t.includes(q))
  })
})

const qtys = ref<Record<string, number>>({})
function qtyFor(id: string) {
  return qtys.value[id] ?? 1
}
function pick(item: Item) {
  emit("pick", { item, qty: Math.max(1, qtyFor(item.id)) })
  open.value = false
}

// --- create new item -------------------------------------------------------
const draft = ref<Item>(blankItem())
function blankItem(): Item {
  return {
    id: "",
    name: "",
    category: "gear",
    rarity: "common",
    weight: 0,
    valueGp: 0,
    description: "",
  }
}
const canCreate = computed(() => draft.value.name.trim().length > 1)
function createItem() {
  const name = draft.value.name.trim()
  const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + Date.now().toString(36)
  const item: Item = { ...draft.value, id, name }
  store.createLibraryItem(item)
  emit("pick", { item, qty: 1 })
  draft.value = blankItem()
  tab.value = "library"
  open.value = false
}
</script>

<template>
  <v-dialog v-model="open" max-width="720" scrollable>
    <v-card color="surface">
      <v-card-title class="picker-title">
        <span class="font-display">Add Item</span>
        <v-btn icon="mdi-close" variant="text" size="small" @click="open = false" />
      </v-card-title>

      <v-tabs v-model="tab" color="primary" density="compact">
        <v-tab value="library"><v-icon start icon="mdi-bookshelf" />Item Library</v-tab>
        <v-tab value="create"><v-icon start icon="mdi-plus-box" />Create New</v-tab>
      </v-tabs>
      <v-divider />

      <v-card-text style="max-height: 60vh">
        <!-- Library picker -->
        <div v-if="tab === 'library'">
          <div class="picker-tools">
            <v-text-field
              v-model="search"
              placeholder="Search library"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
            />
          </div>
          <div class="cat-chips">
            <v-chip
              v-for="cat in CATEGORIES"
              :key="cat"
              size="small"
              :variant="categoryFilter === cat ? 'flat' : 'tonal'"
              :color="categoryFilter === cat ? 'primary' : undefined"
              class="text-capitalize"
              @click="categoryFilter = cat"
            >
              {{ cat }}
            </v-chip>
          </div>

          <div class="lib-list">
            <div v-for="item in results" :key="item.id" class="lib-row">
              <div class="lib-row__main">
                <div class="lib-row__name">
                  {{ item.name }}
                  <v-icon v-if="item.attunement" size="13" icon="mdi-star-circle" color="secondary" class="ml-1" />
                </div>
                <div class="lib-row__meta">
                  <span class="text-capitalize" :style="{ color: rarityColor[item.rarity] }">{{ item.rarity }}</span>
                  <span class="dot">·</span><span class="text-capitalize">{{ item.category }}</span>
                  <span class="dot">·</span>{{ item.weight }} lb
                  <span class="dot">·</span>{{ formatGold(item.valueGp) }}
                </div>
              </div>
              <v-text-field
                :model-value="qtyFor(item.id)"
                type="number"
                min="1"
                density="compact"
                hide-details
                class="lib-row__qty tabular"
                @update:model-value="(v) => (qtys[item.id] = Math.max(1, Number(v) || 1))"
              />
              <v-btn size="small" color="primary" variant="flat" @click="pick(item)">Add</v-btn>
            </div>
            <div v-if="!results.length" class="empty">No items match your search.</div>
          </div>
        </div>

        <!-- Create new item -->
        <div v-else class="create-form">
          <v-text-field v-model="draft.name" label="Item name" density="comfortable" autofocus />
          <div class="create-row">
            <v-select v-model="draft.category" :items="CATEGORIES.filter(c => c !== 'all')" label="Category" class="text-capitalize" />
            <v-select v-model="draft.rarity" :items="RARITIES" label="Rarity" class="text-capitalize" />
          </div>
          <div class="create-row">
            <v-text-field v-model.number="draft.weight" type="number" min="0" label="Weight (lb)" />
            <v-text-field v-model.number="draft.valueGp" type="number" min="0" label="Value (gp)" />
          </div>
          <v-switch v-model="draft.attunement" label="Requires attunement" color="secondary" density="compact" hide-details inset />
          <v-textarea v-model="draft.description" label="Description" rows="3" auto-grow density="comfortable" />
          <v-btn color="primary" variant="flat" block :disabled="!canCreate" prepend-icon="mdi-plus" @click="createItem">
            Create &amp; Add to Inventory
          </v-btn>
          <p class="create-note">New items are saved to the campaign library so the GM and other players can reuse them.</p>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.picker-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.2rem;
}
.picker-tools {
  margin-bottom: 12px;
}
.cat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.lib-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lib-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
}
.lib-row__main {
  flex: 1;
  min-width: 0;
}
.lib-row__name {
  font-weight: 600;
  font-size: 0.9rem;
}
.lib-row__meta {
  font-size: 0.72rem;
  opacity: 0.6;
}
.lib-row__qty {
  width: 72px;
}
.lib-row__qty :deep(input) {
  text-align: center;
}
.create-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 8px;
}
.create-row {
  display: flex;
  gap: 12px;
}
.create-note {
  font-size: 0.75rem;
  opacity: 0.55;
  margin: 0;
}
.empty {
  text-align: center;
  opacity: 0.5;
  padding: 24px 0;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
</style>
