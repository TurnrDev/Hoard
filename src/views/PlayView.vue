<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"
import HpRing from "@/components/HpRing.vue"
import HpControls from "@/components/HpControls.vue"
import AbilityBlock from "@/components/AbilityBlock.vue"
import { ABILITY_NAME, formatMod, modFor, xpProgress } from "@/lib/dnd"
import type { Condition } from "@/types"

const store = useCampaign()
const c = computed(() => store.selected)

const ALL_CONDITIONS: Condition[] = [
  "blinded", "charmed", "frightened", "grappled", "poisoned",
  "prone", "restrained", "stunned", "unconscious", "concentrating",
]

const xp = computed(() => xpProgress(c.value.xp))

const combatStats = computed(() => [
  { label: "Armor Class", value: c.value.ac, icon: "mdi-shield" },
  { label: "Initiative", value: formatMod(c.value.initiative), icon: "mdi-flash" },
  { label: "Speed", value: `${c.value.speed} ft`, icon: "mdi-run-fast" },
  { label: "Prof. Bonus", value: formatMod(c.value.proficiencyBonus), icon: "mdi-plus-circle" },
  { label: "Hit Dice", value: c.value.hitDice, icon: "mdi-dice-d6" },
  { label: "Passive Per.", value: c.value.passivePerception, icon: "mdi-eye" },
])

function isActive(cond: Condition) {
  return c.value.conditions.includes(cond)
}
</script>

<template>
  <div class="view">
    <!-- Character header -->
    <header class="char-head">
      <div class="char-head__avatar font-display" :style="{ background: c.avatarColor }">
        {{ c.initials }}
      </div>
      <div class="char-head__meta">
        <h1 class="char-head__name font-display text-pretty">{{ c.name }}</h1>
        <div class="char-head__line">
          Level {{ c.level }} {{ c.race }} {{ c.class }}
          <span class="dot">·</span> {{ c.subclass }}
        </div>
        <div class="char-head__player micro-label">Played by {{ c.playerName }}</div>
      </div>
      <div class="char-head__xp">
        <div class="micro-label">XP · {{ c.xp.toLocaleString() }}</div>
        <v-progress-linear
          :model-value="xp.pct"
          color="secondary"
          height="6"
          rounded
          class="mt-1"
        />
        <div class="char-head__xptext">{{ xp.into.toLocaleString() }} / {{ xp.span.toLocaleString() }} to L{{ xp.level + 1 }}</div>
      </div>
    </header>

    <div class="grid">
      <!-- HP card, the signature element -->
      <v-card class="pa-5 hp-card" color="surface-bright">
        <div class="hp-card__ring">
          <HpRing :hp="c.hp" :max-hp="c.maxHp" :temp-hp="c.tempHp" :size="180" :stroke="14" />
        </div>
        <HpControls :character-id="c.id" />
        <v-btn
          variant="text"
          size="small"
          color="secondary"
          prepend-icon="mdi-sleep"
          class="mt-3"
          block
          @click="store.longRest(c.id)"
        >
          Long Rest
        </v-btn>
      </v-card>

      <!-- Combat stats -->
      <v-card class="pa-4" color="surface">
        <div class="micro-label mb-3">Combat</div>
        <div class="stat-grid">
          <div v-for="s in combatStats" :key="s.label" class="stat">
            <v-icon :icon="s.icon" size="18" color="primary" class="mb-1" />
            <div class="stat__value font-display tabular">{{ s.value }}</div>
            <div class="stat__label">{{ s.label }}</div>
          </div>
        </div>

        <v-divider class="my-4" />

        <div class="micro-label mb-2">Saving Throws</div>
        <div class="saves">
          <v-chip
            v-for="key in (['str','dex','con','int','wis','cha'] as const)"
            :key="key"
            size="small"
            :variant="c.savingThrows.includes(key) ? 'flat' : 'tonal'"
            :color="c.savingThrows.includes(key) ? 'primary' : undefined"
            class="tabular"
          >
            {{ key.toUpperCase() }}
            {{ formatMod(modFor(c.abilities, key) + (c.savingThrows.includes(key) ? c.proficiencyBonus : 0)) }}
          </v-chip>
        </div>
      </v-card>

      <!-- Abilities -->
      <v-card class="pa-4" color="surface">
        <div class="micro-label mb-3">Ability Scores</div>
        <AbilityBlock :abilities="c.abilities" />
        <v-divider class="my-4" />
        <div class="micro-label mb-2">Skills</div>
        <div class="skills">
          <v-chip v-for="sk in c.skills" :key="sk" size="small" variant="tonal">{{ sk }}</v-chip>
        </div>
      </v-card>

      <!-- Conditions -->
      <v-card class="pa-4" color="surface">
        <div class="micro-label mb-3">Conditions</div>
        <div class="conditions">
          <v-chip
            v-for="cond in ALL_CONDITIONS"
            :key="cond"
            size="small"
            :variant="isActive(cond) ? 'flat' : 'outlined'"
            :color="isActive(cond) ? 'warning' : undefined"
            class="text-capitalize"
            @click="store.toggleCondition(c.id, cond)"
          >
            <v-icon
              start
              size="14"
              :icon="isActive(cond) ? 'mdi-check-circle' : 'mdi-circle-outline'"
            />
            {{ cond }}
          </v-chip>
        </div>
      </v-card>

      <!-- Spell slots (only for casters) -->
      <v-card v-if="c.spellcaster && c.slots.length" class="pa-4 slots-card" color="surface">
        <div class="d-flex align-center justify-space-between mb-3">
          <div class="micro-label">Spell Slots</div>
          <router-link to="/spells" class="link">Manage spells</router-link>
        </div>
        <div class="slot-tiers">
          <div v-for="tier in c.slots" :key="tier.level" class="slot-tier">
            <div class="slot-tier__label">Level {{ tier.level }}</div>
            <div class="slot-pips">
              <button
                v-for="n in tier.total"
                :key="n"
                type="button"
                class="pip"
                :class="{ 'pip--used': n <= tier.used }"
                :aria-label="`Level ${tier.level} slot ${n}`"
                @click="n <= tier.used ? store.restoreSlot(c.id, tier.level) : store.useSlot(c.id, tier.level)"
              />
            </div>
            <div class="slot-tier__count tabular">{{ tier.total - tier.used }}/{{ tier.total }}</div>
          </div>
        </div>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.char-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.char-head__avatar {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 1.5rem;
  font-weight: 700;
  color: #0b0e12;
  flex-shrink: 0;
}
.char-head__meta {
  min-width: 0;
  flex: 1;
}
.char-head__name {
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
}
.char-head__line {
  opacity: 0.75;
  font-size: 0.92rem;
  margin-top: 2px;
}
.char-head__player {
  margin-top: 4px;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
.char-head__xp {
  width: 200px;
}
.char-head__xptext {
  font-size: 0.7rem;
  opacity: 0.55;
  margin-top: 3px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
}
.hp-card {
  grid-column: span 4;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.hp-card__ring {
  margin-bottom: 16px;
}
.grid > .v-card:nth-child(2) {
  grid-column: span 8;
}
.grid > .v-card:nth-child(3) {
  grid-column: span 7;
}
.grid > .v-card:nth-child(4) {
  grid-column: span 5;
}
.slots-card {
  grid-column: span 12;
}

@media (max-width: 900px) {
  .hp-card,
  .grid > .v-card:nth-child(2),
  .grid > .v-card:nth-child(3),
  .grid > .v-card:nth-child(4) {
    grid-column: span 12;
  }
  .char-head__xp {
    width: 100%;
  }
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
@media (min-width: 600px) {
  .stat-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 4px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  text-align: center;
}
.stat__value {
  font-size: 1.3rem;
  font-weight: 700;
}
.stat__label {
  font-size: 0.68rem;
  opacity: 0.55;
  margin-top: 2px;
}
.saves,
.skills,
.conditions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.conditions .v-chip {
  cursor: pointer;
}
.link {
  color: rgb(var(--v-theme-primary));
  font-size: 0.78rem;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}
.slot-tiers {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}
.slot-tier {
  display: flex;
  align-items: center;
  gap: 10px;
}
.slot-tier__label {
  font-size: 0.8rem;
  font-weight: 600;
  min-width: 58px;
}
.slot-pips {
  display: flex;
  gap: 6px;
}
.pip {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid rgb(var(--v-theme-primary));
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease;
}
.pip--used {
  background: rgb(var(--v-theme-primary));
}
.slot-tier__count {
  font-size: 0.8rem;
  opacity: 0.6;
}
</style>
