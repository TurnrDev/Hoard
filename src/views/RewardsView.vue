<script setup lang="ts">
import { computed, ref } from "vue"
import { useCampaign } from "@/stores/campaign"
import { splitXp, xpProgress } from "@/lib/dnd"
import {
  COIN_COLOR,
  COIN_LABEL,
  COIN_ORDER,
  coinsToGold,
  emptyCoins,
  formatGold,
} from "@/lib/money"
import ItemPicker from "@/components/ItemPicker.vue"
import type { Coins, Item } from "@/types"

const store = useCampaign()
const party = computed(() => store.party)

// --- XP award ----------------------------------------------------------
const xpTotal = ref<number>(0)
const xpSplit = computed(() => splitXp(Number(xpTotal.value) || 0, party.value.length))

function awardXp() {
  const each = xpSplit.value.each
  if (each <= 0) return
  store.awardXpToParty(each)
  store.addLedgerEntry({
    timestamp: "Just now",
    type: "xp",
    summary: `Awarded ${each} XP to the party`,
    detail: `${xpTotal.value} XP split across ${party.value.length} adventurers`,
    xpEach: each,
  })
  xpTotal.value = 0
}

// --- Gold split --------------------------------------------------------
const goldPool = ref<Coins>(emptyCoins())
const poolGold = computed(() => coinsToGold(goldPool.value))
const goldEach = computed(() => {
  const per = poolGold.value / Math.max(1, party.value.length)
  return Math.floor(per * 100) / 100
})

function distributeGold() {
  if (goldEach.value <= 0) return
  const gp = Math.floor(goldEach.value)
  const sp = Math.round((goldEach.value - gp) * 10)
  party.value.forEach((c) => store.adjustCoins(c.id, { gp, sp }))
  store.addLedgerEntry({
    timestamp: "Just now",
    type: "gold",
    summary: `Split ${formatGold(poolGold.value)} among the party`,
    detail: `${formatGold(goldEach.value)} each`,
    coins: { gp, sp },
  })
  goldPool.value = emptyCoins()
}

// --- Loot hand-out -----------------------------------------------------
const lootTarget = ref<string>(party.value[0]?.id ?? "")
const pickerOpen = ref(false)

function handleLoot(payload: { item: Item; qty: number }) {
  const { item, qty } = payload
  store.createLibraryItem(item)
  store.addInventory(lootTarget.value, { itemId: item.id, qty })
  const who = store.charById(lootTarget.value)
  store.addLedgerEntry({
    timestamp: "Just now",
    type: "loot",
    summary: `${who?.name ?? "A hero"} received ${qty}× ${item.name}`,
    items: [{ name: item.name, qty }],
  })
  pickerOpen.value = false
}
</script>

<template>
  <div class="view">
    <header class="page-head">
      <div>
        <div class="micro-label">Game Master</div>
        <h1 class="page-title font-display">Distribute Rewards</h1>
      </div>
    </header>

    <div class="grid">
      <!-- XP -->
      <v-card class="reward-card pa-5" color="surface">
        <div class="reward-head">
          <v-avatar size="40" color="secondary" variant="tonal">
            <v-icon icon="mdi-star-four-points" />
          </v-avatar>
          <div>
            <h2 class="reward-title font-display">Experience</h2>
            <p class="reward-sub">Split evenly across the whole party</p>
          </div>
        </div>

        <v-text-field
          v-model.number="xpTotal"
          type="number"
          label="Total XP to award"
          variant="outlined"
          density="comfortable"
          min="0"
          prepend-inner-icon="mdi-star-four-points"
          class="mt-4"
        />

        <div class="split-readout">
          <div class="split-readout__each">
            <span class="split-readout__num font-display tabular">{{ xpSplit.each }}</span>
            <span class="split-readout__label">XP each · {{ party.length }} heroes</span>
          </div>
          <v-chip v-if="xpSplit.remainder > 0" size="small" color="warning" variant="tonal">
            {{ xpSplit.remainder }} XP remainder
          </v-chip>
        </div>

        <v-btn
          block
          color="secondary"
          variant="flat"
          class="mt-4"
          prepend-icon="mdi-check"
          :disabled="xpSplit.each <= 0"
          @click="awardXp"
        >
          Award to Party
        </v-btn>

        <div class="preview-list mt-4">
          <div v-for="c in party" :key="c.id" class="preview-row">
            <span class="preview-row__name">
              <span class="preview-row__dot" :style="{ background: c.avatarColor }" />
              {{ c.name }}
            </span>
            <span class="preview-row__val tabular">
              L{{ xpProgress(c.xp + xpSplit.each).level }}
              <span class="preview-row__delta" v-if="xpSplit.each > 0">
                ({{ c.xp.toLocaleString() }} → {{ (c.xp + xpSplit.each).toLocaleString() }})
              </span>
            </span>
          </div>
        </div>
      </v-card>

      <!-- Gold -->
      <v-card class="reward-card pa-5" color="surface">
        <div class="reward-head">
          <v-avatar size="40" color="primary" variant="tonal">
            <v-icon icon="mdi-circle-multiple" />
          </v-avatar>
          <div>
            <h2 class="reward-title font-display">Treasure Hoard</h2>
            <p class="reward-sub">Pool coins, then split evenly</p>
          </div>
        </div>

        <div class="coin-grid mt-4">
          <div v-for="k in COIN_ORDER" :key="k" class="coin-field">
            <label class="coin-field__label">
              <span class="coin-field__dot" :style="{ background: COIN_COLOR[k] }" />
              {{ COIN_LABEL[k] }}
            </label>
            <v-text-field
              v-model.number="goldPool[k]"
              type="number"
              variant="outlined"
              density="compact"
              min="0"
              hide-details
              :suffix="k"
            />
          </div>
        </div>

        <div class="split-readout mt-4">
          <div class="split-readout__each">
            <span class="split-readout__num font-display tabular">{{ formatGold(poolGold) }}</span>
            <span class="split-readout__label">pooled · {{ formatGold(goldEach) }} each</span>
          </div>
        </div>

        <v-btn
          block
          color="primary"
          variant="flat"
          class="mt-4"
          prepend-icon="mdi-hand-coin"
          :disabled="goldEach <= 0"
          @click="distributeGold"
        >
          Split Among Party
        </v-btn>
      </v-card>

      <!-- Loot -->
      <v-card class="reward-card pa-5" color="surface">
        <div class="reward-head">
          <v-avatar size="40" color="warning" variant="tonal">
            <v-icon icon="mdi-treasure-chest" />
          </v-avatar>
          <div>
            <h2 class="reward-title font-display">Hand Out Loot</h2>
            <p class="reward-sub">Give a specific item to one hero</p>
          </div>
        </div>

        <v-select
          v-model="lootTarget"
          :items="party.map((c) => ({ title: c.name, value: c.id }))"
          label="Recipient"
          variant="outlined"
          density="comfortable"
          prepend-inner-icon="mdi-account"
          class="mt-4"
        />

        <v-btn
          block
          color="warning"
          variant="tonal"
          prepend-icon="mdi-plus"
          @click="pickerOpen = true"
        >
          Choose Item to Award
        </v-btn>

        <p class="loot-hint mt-3">
          Pick from the shared item library or forge a brand-new item on the spot.
        </p>
      </v-card>
    </div>

    <ItemPicker v-model="pickerOpen" @select="handleLoot" />
  </div>
</template>

<style scoped>
.view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.page-head {
  margin-bottom: 20px;
}
.page-title {
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1.1;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  align-items: start;
}
.reward-card {
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.reward-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.reward-title {
  font-size: 1.2rem;
  font-weight: 600;
  line-height: 1.1;
}
.reward-sub {
  font-size: 0.8rem;
  opacity: 0.6;
}
.split-readout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.split-readout__each {
  display: flex;
  flex-direction: column;
}
.split-readout__num {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
  color: rgb(var(--v-theme-primary));
}
.split-readout__label {
  font-size: 0.72rem;
  opacity: 0.6;
  margin-top: 3px;
}
.coin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}
.coin-field__label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  opacity: 0.7;
  margin-bottom: 4px;
}
.coin-field__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.preview-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.preview-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.82rem;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.preview-row__name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.preview-row__dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
.preview-row__val {
  opacity: 0.85;
  font-weight: 600;
}
.preview-row__delta {
  opacity: 0.5;
  font-weight: 400;
  font-size: 0.72rem;
}
.loot-hint {
  font-size: 0.76rem;
  opacity: 0.55;
  text-align: center;
}
</style>
