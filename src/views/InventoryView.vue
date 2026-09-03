<script setup lang="ts">
import { computed, ref } from "vue"
import { useCampaign } from "@/stores/campaign"
import CoinEditor from "@/components/CoinEditor.vue"
import ItemPicker from "@/components/ItemPicker.vue"
import { formatGold } from "@/lib/money"
import type { Coins, Item, ItemRarity } from "@/types"

const store = useCampaign()
const c = computed(() => store.selected)
const itemMap = computed(() => store.itemMap)

const pickerOpen = ref(false)

const rarityColor: Record<ItemRarity, string> = {
  common: "#94a3b8",
  uncommon: "#34d399",
  rare: "#38bdf8",
  "very rare": "#a78bfa",
  legendary: "#fbbf24",
}
const categoryIcon: Record<string, string> = {
  weapon: "mdi-sword",
  armor: "mdi-shield",
  consumable: "mdi-flask-round-bottom",
  gear: "mdi-bag-personal",
  treasure: "mdi-diamond-stone",
  wondrous: "mdi-auto-fix",
  tool: "mdi-tools",
}

// resolved inventory rows joined with the library
const rows = computed(() =>
  c.value.inventory
    .map((entry) => ({ entry, item: itemMap.value[entry.itemId] as Item | undefined }))
    .filter((r) => r.item),
)

const totalWeight = computed(() =>
  rows.value.reduce((sum, r) => sum + (r.item?.weight ?? 0) * r.entry.qty, 0),
)
const totalItemValue = computed(() =>
  rows.value.reduce((sum, r) => sum + (r.item?.valueGp ?? 0) * r.entry.qty, 0),
)
const carryCapacity = computed(() => c.value.abilities.str * 15)
const encumbered = computed(() => totalWeight.value > carryCapacity.value)

function updateCoins(coins: Coins) {
  store.setCoins(c.value.id, coins)
}
function onPick(payload: { item: Item; qty: number }) {
  store.createLibraryItem(payload.item)
  store.addInventory(c.value.id, { itemId: payload.item.id, qty: payload.qty })
}
</script>

<template>
  <div class="view">
    <div class="layout">
      <!-- Money column -->
      <div class="money-col">
        <v-card class="pa-4" color="surface-bright">
          <div class="d-flex align-center mb-4">
            <v-icon icon="mdi-sack" color="primary" class="mr-2" />
            <h2 class="font-display card-title">Coin Purse</h2>
          </div>
          <CoinEditor :model-value="c.coins" @update:model-value="updateCoins" />

          <v-divider class="my-4" />
          <div class="quick-add">
            <div class="micro-label mb-2">Quick Adjust (Gold)</div>
            <div class="quick-add__btns">
              <v-btn size="small" variant="tonal" color="hp-healthy" @click="store.adjustCoins(c.id, { gp: 10 })">+10</v-btn>
              <v-btn size="small" variant="tonal" color="hp-healthy" @click="store.adjustCoins(c.id, { gp: 50 })">+50</v-btn>
              <v-btn size="small" variant="tonal" color="hp-danger" @click="store.adjustCoins(c.id, { gp: -10 })">-10</v-btn>
              <v-btn size="small" variant="tonal" color="hp-danger" @click="store.adjustCoins(c.id, { gp: -50 })">-50</v-btn>
            </div>
          </div>
        </v-card>

        <v-card class="pa-4 mt-4" color="surface">
          <div class="micro-label mb-3">Load</div>
          <div class="load-row">
            <span>Carried</span>
            <span class="tabular" :class="{ 'text-error': encumbered }">{{ totalWeight.toFixed(1) }} lb</span>
          </div>
          <v-progress-linear
            :model-value="Math.min(100, (totalWeight / carryCapacity) * 100)"
            :color="encumbered ? 'error' : 'primary'"
            height="6"
            rounded
            class="my-2"
          />
          <div class="load-row load-row--sub">
            <span>Capacity</span>
            <span class="tabular">{{ carryCapacity }} lb</span>
          </div>
          <v-alert v-if="encumbered" type="warning" density="compact" variant="tonal" class="mt-2">
            Encumbered — speed reduced.
          </v-alert>
          <v-divider class="my-3" />
          <div class="load-row">
            <span>Item Value</span>
            <span class="tabular font-display">{{ formatGold(totalItemValue) }}</span>
          </div>
        </v-card>
      </div>

      <!-- Inventory column -->
      <div class="inv-col">
        <div class="section-head">
          <h2 class="font-display card-title">
            Inventory
            <span class="count">{{ rows.length }}</span>
          </h2>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" @click="pickerOpen = true">
            Add Item
          </v-btn>
        </div>

        <v-card
          v-for="{ entry, item } in rows"
          :key="entry.itemId"
          class="inv-item pa-3 mb-2"
          color="surface"
        >
          <v-avatar :color="'surface-variant'" size="42" rounded="lg" class="inv-item__icon">
            <v-icon :icon="categoryIcon[item!.category]" :color="rarityColor[item!.rarity]" />
          </v-avatar>

          <div class="inv-item__main">
            <div class="inv-item__name">
              {{ item!.name }}
              <v-chip
                v-if="entry.equipped"
                size="x-small"
                color="primary"
                variant="flat"
                class="ml-1"
              >
                Equipped
              </v-chip>
              <v-chip
                v-if="entry.attuned"
                size="x-small"
                color="secondary"
                variant="tonal"
                class="ml-1"
              >
                Attuned
              </v-chip>
            </div>
            <div class="inv-item__meta">
              <span class="text-capitalize" :style="{ color: rarityColor[item!.rarity] }">{{ item!.rarity }}</span>
              <span class="dot">·</span>{{ (item!.weight * entry.qty).toFixed(1) }} lb
              <span class="dot">·</span>{{ formatGold(item!.valueGp * entry.qty) }}
            </div>
            <p class="inv-item__desc">{{ item!.description }}</p>
          </div>

          <div class="inv-item__actions">
            <div class="qty-stepper">
              <v-btn icon="mdi-minus" size="x-small" variant="text" @click="store.setInventoryQty(c.id, entry.itemId, entry.qty - 1)" />
              <span class="qty-stepper__n tabular">{{ entry.qty }}</span>
              <v-btn icon="mdi-plus" size="x-small" variant="text" @click="store.setInventoryQty(c.id, entry.itemId, entry.qty + 1)" />
            </div>
            <div class="inv-item__buttons">
              <v-btn
                size="x-small"
                variant="text"
                :color="entry.equipped ? 'primary' : undefined"
                :icon="entry.equipped ? 'mdi-hand-back-right' : 'mdi-hand-back-right-outline'"
                :aria-label="entry.equipped ? 'Unequip' : 'Equip'"
                @click="store.toggleEquipped(c.id, entry.itemId)"
              />
              <v-btn
                size="x-small"
                variant="text"
                color="error"
                icon="mdi-trash-can-outline"
                aria-label="Remove"
                @click="store.removeInventory(c.id, entry.itemId)"
              />
            </div>
          </div>
        </v-card>

        <div v-if="!rows.length" class="empty">
          <v-icon size="40" icon="mdi-bag-personal-off" class="mb-2" />
          <div>No items yet. Add something from the library.</div>
        </div>
      </div>
    </div>

    <ItemPicker v-model="pickerOpen" @pick="onPick" />
  </div>
</template>

<style scoped>
.view {
  max-width: 1150px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: start;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
.card-title {
  font-size: 1.15rem;
  font-weight: 600;
}
.quick-add__btns {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.load-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.88rem;
}
.load-row--sub {
  opacity: 0.6;
  font-size: 0.78rem;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.count {
  display: inline-grid;
  place-items: center;
  min-width: 24px;
  height: 22px;
  padding: 0 6px;
  margin-left: 6px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.75rem;
  vertical-align: middle;
}
.inv-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.inv-item__icon {
  flex-shrink: 0;
}
.inv-item__main {
  flex: 1;
  min-width: 0;
}
.inv-item__name {
  font-weight: 600;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}
.inv-item__meta {
  font-size: 0.75rem;
  opacity: 0.65;
  margin: 2px 0 4px;
}
.inv-item__desc {
  font-size: 0.8rem;
  line-height: 1.45;
  opacity: 0.8;
  margin: 0;
}
.inv-item__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.qty-stepper {
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
}
.qty-stepper__n {
  min-width: 22px;
  text-align: center;
  font-weight: 600;
  font-size: 0.85rem;
}
.empty {
  text-align: center;
  opacity: 0.5;
  padding: 48px 0;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
</style>
