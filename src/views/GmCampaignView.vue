<script setup lang="ts">
import { computed } from "vue"
import { useRouter } from "vue-router"
import { useCampaign } from "@/stores/campaign"
import { coinsToGold, formatGold } from "@/lib/money"
import { levelForXp } from "@/lib/dnd"
import type { Character, LedgerEntry } from "@/types"

const store = useCampaign()
const router = useRouter()
const camp = computed(() => store.campaign)
const enc = computed(() => store.activeEncounter)

const partyGold = computed(() =>
  formatGold(camp.value.characters.reduce((sum, c) => sum + coinsToGold(c.coins), 0)),
)
const avgLevel = computed(() => {
  const total = camp.value.characters.reduce((s, c) => s + c.level, 0)
  return (total / camp.value.characters.length).toFixed(1)
})
const downed = computed(() => camp.value.characters.filter((c) => c.hp <= 0).length)

function hpRatio(c: Character) {
  return c.maxHp > 0 ? c.hp / c.maxHp : 0
}
function hpColor(c: Character) {
  if (c.hp <= 0) return "hp-down"
  const r = hpRatio(c)
  if (r <= 0.25) return "hp-danger"
  if (r <= 0.5) return "hp-wounded"
  return "hp-healthy"
}

const ledgerIcon: Record<LedgerEntry["type"], string> = {
  xp: "mdi-star-four-points",
  loot: "mdi-treasure-chest",
  gold: "mdi-circle-multiple",
  note: "mdi-note-text",
}
const ledgerColor: Record<LedgerEntry["type"], string> = {
  xp: "secondary",
  loot: "warning",
  gold: "primary",
  note: "info",
}

function inspect(id: string) {
  store.selectCharacter(id)
  router.push("/play")
}
</script>

<template>
  <div class="view">
    <!-- Campaign banner -->
    <v-card class="banner pa-5 mb-4" color="surface-bright">
      <div class="banner__main">
        <div>
          <div class="micro-label">Campaign</div>
          <h1 class="banner__title font-display text-pretty">{{ camp.name }}</h1>
          <div class="banner__sub">
            GM {{ camp.gmName }} <span class="dot">·</span> {{ camp.setting }}
          </div>
        </div>
        <div class="banner__next">
          <div class="micro-label">Next Session</div>
          <div class="banner__next-val">{{ camp.nextSession }}</div>
          <v-chip size="small" color="secondary" variant="tonal" class="mt-1">
            Session {{ camp.sessionNumber }}
          </v-chip>
        </div>
      </div>

      <div class="banner__stats">
        <div class="bstat">
          <div class="bstat__value font-display">{{ camp.characters.length }}</div>
          <div class="bstat__label">Adventurers</div>
        </div>
        <div class="bstat">
          <div class="bstat__value font-display">{{ avgLevel }}</div>
          <div class="bstat__label">Avg Level</div>
        </div>
        <div class="bstat">
          <div class="bstat__value font-display tabular">{{ partyGold }}</div>
          <div class="bstat__label">Party Wealth</div>
        </div>
        <div class="bstat" :class="{ 'bstat--alert': downed > 0 }">
          <div class="bstat__value font-display">{{ downed }}</div>
          <div class="bstat__label">Downed</div>
        </div>
      </div>
    </v-card>

    <div class="cols">
      <!-- Party roster -->
      <section class="col-main">
        <div class="section-head">
          <h2 class="section-title font-display">Party Roster</h2>
          <v-btn size="small" variant="tonal" color="secondary" prepend-icon="mdi-treasure-chest" to="/gm/rewards">
            Distribute Rewards
          </v-btn>
        </div>

        <v-card
          v-for="c in camp.characters"
          :key="c.id"
          class="roster pa-3 mb-3"
          color="surface"
          @click="inspect(c.id)"
        >
          <div class="roster__avatar font-display" :style="{ background: c.avatarColor }">
            {{ c.initials }}
            <span v-if="c.conditions.length" class="roster__cond">{{ c.conditions.length }}</span>
          </div>
          <div class="roster__meta">
            <div class="roster__name">{{ c.name }}</div>
            <div class="roster__class">
              L{{ c.level }} {{ c.race }} {{ c.class }}
              <span class="dot">·</span> {{ c.playerName }}
            </div>
            <div class="roster__conds" v-if="c.conditions.length">
              <v-chip
                v-for="cond in c.conditions"
                :key="cond"
                size="x-small"
                color="warning"
                variant="tonal"
                class="text-capitalize"
              >
                {{ cond }}
              </v-chip>
            </div>
          </div>
          <div class="roster__combat">
            <div class="roster__ac">
              <v-icon size="16" icon="mdi-shield" />
              <span class="tabular">{{ c.ac }}</span>
            </div>
            <div class="roster__hp">
              <div class="roster__hpbar">
                <div class="roster__hpfill" :class="`bar-${hpColor(c)}`" :style="{ width: `${Math.max(0, hpRatio(c) * 100)}%` }" />
              </div>
              <span class="roster__hptext tabular">
                <template v-if="c.hp <= 0">Down</template>
                <template v-else>{{ c.hp }}/{{ c.maxHp }}</template>
              </span>
            </div>
          </div>
        </v-card>
      </section>

      <!-- Sidebar: active encounter + ledger -->
      <aside class="col-side">
        <div class="section-head">
          <h2 class="section-title font-display">Active Encounter</h2>
        </div>
        <v-card class="pa-4 mb-4" :color="enc?.active ? 'surface-bright' : 'surface'">
          <template v-if="enc">
            <div class="enc-head">
              <div>
                <div class="enc-name font-display">{{ enc.name }}</div>
                <div class="enc-sub">Round {{ enc.round }} <span class="dot">·</span> {{ enc.combatants.length }} combatants</div>
              </div>
              <v-chip size="small" :color="enc.active ? 'success' : undefined" variant="flat" v-if="enc.active">
                Live
              </v-chip>
            </div>
            <div class="enc-turn">
              <div class="micro-label mb-1">On Deck</div>
              <div class="enc-turn__name">
                <v-icon size="16" icon="mdi-sword" color="primary" class="mr-1" />
                {{ enc.combatants[enc.activeIndex]?.name }}
              </div>
            </div>
            <v-btn block color="primary" variant="flat" prepend-icon="mdi-sword" class="mt-3" to="/gm/encounter">
              Open Tracker
            </v-btn>
          </template>
          <template v-else>
            <div class="empty">No active encounter.</div>
          </template>
        </v-card>

        <div class="section-head">
          <h2 class="section-title font-display">Campaign Ledger</h2>
        </div>
        <v-card class="pa-2" color="surface">
          <v-list bg-color="transparent" density="comfortable">
            <v-list-item v-for="entry in camp.ledger" :key="entry.id" class="ledger-item">
              <template #prepend>
                <v-avatar size="34" :color="ledgerColor[entry.type]" variant="tonal">
                  <v-icon size="18" :icon="ledgerIcon[entry.type]" />
                </v-avatar>
              </template>
              <v-list-item-title class="ledger-title">{{ entry.summary }}</v-list-item-title>
              <v-list-item-subtitle class="ledger-sub">
                {{ entry.timestamp }}
                <template v-if="entry.xpEach"> <span class="dot">·</span> +{{ entry.xpEach }} XP each</template>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.banner__main {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.banner__title {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 2px 0;
}
.banner__sub {
  opacity: 0.7;
}
.banner__next {
  text-align: right;
}
.banner__next-val {
  font-weight: 600;
  font-size: 0.95rem;
}
.banner__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 20px;
}
.bstat {
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  text-align: center;
}
.bstat--alert {
  border-color: rgb(var(--v-theme-error));
  background: color-mix(in srgb, rgb(var(--v-theme-error)) 12%, transparent);
}
.bstat__value {
  font-size: 1.5rem;
  font-weight: 700;
}
.bstat__label {
  font-size: 0.68rem;
  opacity: 0.55;
  margin-top: 2px;
}

.cols {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
}
@media (max-width: 960px) {
  .cols {
    grid-template-columns: 1fr;
  }
  .banner__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.section-title {
  font-size: 1.15rem;
  font-weight: 600;
}

.roster {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: transform 0.12s ease, background 0.15s ease;
}
.roster:hover {
  transform: translateX(2px);
}
.roster__avatar {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 700;
  color: #0b0e12;
  flex-shrink: 0;
}
.roster__cond {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: rgb(var(--v-theme-warning));
  color: #1e1400;
  font-size: 0.65rem;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.roster__meta {
  flex: 1;
  min-width: 0;
}
.roster__name {
  font-weight: 600;
}
.roster__class {
  font-size: 0.8rem;
  opacity: 0.65;
}
.roster__conds {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.roster__combat {
  display: flex;
  align-items: center;
  gap: 16px;
}
.roster__ac {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  opacity: 0.85;
}
.roster__hp {
  width: 120px;
}
.roster__hpbar {
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.roster__hpfill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.bar-hp-healthy { background: #34d399; }
.bar-hp-wounded { background: #fbbf24; }
.bar-hp-danger { background: #f87171; }
.bar-hp-down { background: #64748b; }
.roster__hptext {
  font-size: 0.72rem;
  opacity: 0.7;
  display: block;
  text-align: right;
  margin-top: 2px;
}

.enc-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.enc-name {
  font-size: 1.15rem;
  font-weight: 600;
}
.enc-sub {
  font-size: 0.8rem;
  opacity: 0.65;
}
.enc-turn {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
}
.enc-turn__name {
  font-weight: 600;
  display: flex;
  align-items: center;
}
.empty {
  opacity: 0.5;
  padding: 12px 0;
  text-align: center;
}
.ledger-item {
  border-radius: 10px;
}
.ledger-title {
  font-size: 0.9rem;
  font-weight: 600;
}
.ledger-sub {
  font-size: 0.75rem;
  opacity: 0.6;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
</style>
