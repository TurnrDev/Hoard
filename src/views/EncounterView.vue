<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"
import type { Condition, EncounterCombatant } from "@/types"

const store = useCampaign()
const enc = computed(() => store.activeEncounter)

const CONDITIONS: Condition[] = [
  "blinded",
  "charmed",
  "frightened",
  "grappled",
  "poisoned",
  "prone",
  "restrained",
  "stunned",
  "unconscious",
  "concentrating",
]

const sorted = computed(() => enc.value?.combatants ?? [])

function hpRatio(cb: EncounterCombatant) {
  return cb.maxHp > 0 ? cb.hp / cb.maxHp : 0
}
function hpColor(cb: EncounterCombatant) {
  if (cb.hp <= 0) return "hp-down"
  const r = hpRatio(cb)
  if (r <= 0.25) return "hp-danger"
  if (r <= 0.5) return "hp-wounded"
  return "hp-healthy"
}

const kindMeta: Record<EncounterCombatant["kind"], { color: string; icon: string }> = {
  pc: { color: "primary", icon: "mdi-account-star" },
  npc: { color: "info", icon: "mdi-account" },
  monster: { color: "error", icon: "mdi-skull" },
}

function isActive(index: number) {
  return enc.value?.activeIndex === index
}
</script>

<template>
  <div class="view" v-if="enc">
    <!-- Turn control bar -->
    <v-card class="tracker-bar pa-4 mb-4" color="surface-bright">
      <div class="tracker-bar__info">
        <div class="micro-label">Encounter</div>
        <h1 class="tracker-bar__name font-display">{{ enc.name }}</h1>
      </div>
      <div class="tracker-bar__round">
        <div class="round-badge font-display">
          <span class="round-badge__num tabular">{{ enc.round }}</span>
          <span class="round-badge__label">Round</span>
        </div>
      </div>
      <div class="tracker-bar__controls">
        <v-btn icon="mdi-chevron-left" variant="tonal" size="small" @click="store.prevTurn()" aria-label="Previous turn" />
        <v-btn color="primary" variant="flat" prepend-icon="mdi-skip-next" @click="store.nextTurn()">
          Next Turn
        </v-btn>
        <v-btn icon="mdi-sort-descending" variant="tonal" size="small" @click="store.sortByInitiative()" aria-label="Sort by initiative" />
      </div>
    </v-card>

    <!-- Initiative order -->
    <div class="initiative">
      <div
        v-for="(cb, i) in sorted"
        :key="cb.id"
        class="combatant"
        :class="{ 'combatant--active': isActive(i), 'combatant--down': cb.hp <= 0 }"
      >
        <div class="combatant__init font-display tabular">
          {{ cb.initiative }}
          <span class="combatant__init-label">init</span>
        </div>

        <v-avatar size="42" :color="kindMeta[cb.kind].color" variant="tonal" class="combatant__avatar">
          <v-icon :icon="kindMeta[cb.kind].icon" size="20" />
        </v-avatar>

        <div class="combatant__main">
          <div class="combatant__name-row">
            <span class="combatant__name">{{ cb.name }}</span>
            <v-chip size="x-small" variant="tonal" :color="kindMeta[cb.kind].color" class="text-uppercase">
              {{ cb.kind }}
            </v-chip>
            <v-icon v-if="isActive(i)" icon="mdi-sword" size="16" color="primary" class="combatant__turn-icon" />
          </div>
          <div class="combatant__hpbar">
            <div class="combatant__hpfill" :class="`bar-${hpColor(cb)}`" :style="{ width: `${Math.max(0, hpRatio(cb) * 100)}%` }" />
          </div>
          <div class="combatant__conds" v-if="cb.conditions.length">
            <v-chip
              v-for="cond in cb.conditions"
              :key="cond"
              size="x-small"
              color="warning"
              variant="tonal"
              class="text-capitalize"
              closable
              @click:close="store.toggleCombatantCondition(cb.id, cond)"
            >
              {{ cond }}
            </v-chip>
          </div>
        </div>

        <div class="combatant__stats">
          <div class="combatant__ac">
            <v-icon icon="mdi-shield" size="15" />
            <span class="tabular">{{ cb.ac }}</span>
          </div>
          <div class="combatant__hp">
            <v-btn icon="mdi-minus" size="x-small" variant="text" @click="store.combatantHpDelta(cb.id, -1)" aria-label="Damage" />
            <span class="combatant__hptext tabular" :class="{ 'text-error': cb.hp <= 0 }">
              {{ cb.hp }}<span class="combatant__hpmax">/{{ cb.maxHp }}</span>
            </span>
            <v-btn icon="mdi-plus" size="x-small" variant="text" @click="store.combatantHpDelta(cb.id, 1)" aria-label="Heal" />
          </div>
          <v-menu :close-on-content-click="false">
            <template #activator="{ props }">
              <v-btn v-bind="props" icon="mdi-flask-round-bottom" size="x-small" variant="tonal" color="warning" aria-label="Conditions" />
            </template>
            <v-card color="surface-bright" class="pa-2" min-width="200">
              <div class="micro-label px-2 pb-1">Conditions</div>
              <v-list density="compact" bg-color="transparent">
                <v-list-item
                  v-for="cond in CONDITIONS"
                  :key="cond"
                  class="text-capitalize"
                  @click="store.toggleCombatantCondition(cb.id, cond)"
                >
                  <template #prepend>
                    <v-icon
                      :icon="cb.conditions.includes(cond) ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'"
                      :color="cb.conditions.includes(cond) ? 'warning' : undefined"
                      size="18"
                    />
                  </template>
                  <v-list-item-title class="text-body-2 text-capitalize">{{ cond }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card>
          </v-menu>
        </div>
      </div>
    </div>
  </div>

  <div class="view empty-state" v-else>
    <v-icon icon="mdi-sword-cross" size="48" class="mb-2" />
    <p>No active encounter.</p>
  </div>
</template>

<style scoped>
.view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.tracker-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.tracker-bar__info {
  flex: 1;
  min-width: 160px;
}
.tracker-bar__name {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.1;
}
.round-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 18px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.round-badge__num {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
  color: rgb(var(--v-theme-primary));
}
.round-badge__label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.55;
}
.tracker-bar__controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.initiative {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.combatant {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-left: 3px solid transparent;
  transition: border-color 0.2s ease, transform 0.12s ease, box-shadow 0.2s ease;
}
.combatant--active {
  border-left-color: rgb(var(--v-theme-primary));
  background: color-mix(in srgb, rgb(var(--v-theme-primary)) 8%, rgb(var(--v-theme-surface)));
  box-shadow: 0 0 0 1px color-mix(in srgb, rgb(var(--v-theme-primary)) 30%, transparent);
}
.combatant--down {
  opacity: 0.55;
}
.combatant__init {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40px;
  flex-shrink: 0;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1;
}
.combatant__init-label {
  font-size: 0.58rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.5;
  font-family: var(--v-font-body, inherit);
  font-weight: 400;
}
.combatant__avatar {
  flex-shrink: 0;
}
.combatant__main {
  flex: 1;
  min-width: 0;
}
.combatant__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.combatant__name {
  font-weight: 600;
}
.combatant__turn-icon {
  margin-left: auto;
}
.combatant__hpbar {
  height: 5px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  margin-top: 6px;
}
.combatant__hpfill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.bar-hp-healthy { background: #34d399; }
.bar-hp-wounded { background: #fbbf24; }
.bar-hp-danger { background: #f87171; }
.bar-hp-down { background: #64748b; }
.combatant__conds {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.combatant__stats {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.combatant__ac {
  display: flex;
  align-items: center;
  gap: 3px;
  font-weight: 600;
  opacity: 0.8;
  font-size: 0.9rem;
}
.combatant__hp {
  display: flex;
  align-items: center;
  gap: 2px;
}
.combatant__hptext {
  min-width: 54px;
  text-align: center;
  font-weight: 700;
  font-size: 0.95rem;
}
.combatant__hpmax {
  opacity: 0.5;
  font-weight: 400;
  font-size: 0.8rem;
}
.empty-state {
  text-align: center;
  opacity: 0.5;
  padding-top: 80px;
}
@media (max-width: 640px) {
  .combatant {
    flex-wrap: wrap;
  }
  .combatant__stats {
    width: 100%;
    justify-content: space-between;
    padding-left: 54px;
  }
}
</style>
