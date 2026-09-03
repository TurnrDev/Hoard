<script setup lang="ts">
import { computed, ref } from "vue"
import { useCampaign } from "@/stores/campaign"
import { formatMod } from "@/lib/dnd"
import type { Spell } from "@/types"

const store = useCampaign()
const c = computed(() => store.selected)

const search = ref("")
const showPreparedOnly = ref(false)

const schoolColor: Record<string, string> = {
  abjuration: "#38bdf8",
  conjuration: "#a78bfa",
  divination: "#c4b5fd",
  enchantment: "#f472b6",
  evocation: "#f87171",
  illusion: "#818cf8",
  necromancy: "#64748b",
  transmutation: "#34d399",
}

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return c.value.spells.filter((s) => {
    if (showPreparedOnly.value && !s.prepared && s.level > 0) return false
    if (!q) return true
    return s.name.toLowerCase().includes(q) || s.school.includes(q)
  })
})

const grouped = computed(() => {
  const map = new Map<number, Spell[]>()
  for (const s of filtered.value) {
    if (!map.has(s.level)) map.set(s.level, [])
    map.get(s.level)!.push(s)
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0])
})

function levelLabel(lvl: number) {
  return lvl === 0 ? "Cantrips" : `Level ${lvl}`
}
function slotFor(lvl: number) {
  return c.value.slots.find((t) => t.level === lvl)
}
const preparedCount = computed(() => c.value.spells.filter((s) => s.prepared && s.level > 0).length)
</script>

<template>
  <div class="view">
    <div v-if="!c.spellcaster" class="noncaster">
      <v-icon size="48" icon="mdi-sword-cross" color="primary" class="mb-3" />
      <h2 class="font-display">{{ c.name }} is not a spellcaster</h2>
      <p class="text-medium-emphasis">Martial characters channel their power through features instead.</p>
      <v-btn color="primary" variant="tonal" to="/features" prepend-icon="mdi-star-four-points" class="mt-2">
        View Features
      </v-btn>
    </div>

    <template v-else>
      <!-- Spellcasting summary -->
      <div class="cast-head">
        <div class="cast-stat">
          <div class="cast-stat__value font-display">{{ c.spellAbility?.toUpperCase() }}</div>
          <div class="cast-stat__label">Ability</div>
        </div>
        <div class="cast-stat">
          <div class="cast-stat__value font-display tabular">{{ c.spellSaveDc }}</div>
          <div class="cast-stat__label">Save DC</div>
        </div>
        <div class="cast-stat">
          <div class="cast-stat__value font-display tabular">{{ formatMod(c.spellAttack ?? 0) }}</div>
          <div class="cast-stat__label">Attack</div>
        </div>
        <div class="cast-stat">
          <div class="cast-stat__value font-display tabular">{{ preparedCount }}</div>
          <div class="cast-stat__label">Prepared</div>
        </div>
      </div>

      <div class="toolbar">
        <v-text-field
          v-model="search"
          placeholder="Search spells"
          prepend-inner-icon="mdi-magnify"
          density="comfortable"
          class="toolbar__search"
          clearable
        />
        <v-switch
          v-model="showPreparedOnly"
          label="Prepared only"
          color="primary"
          density="compact"
          hide-details
          inset
        />
      </div>

      <div v-for="[lvl, spells] in grouped" :key="lvl" class="level-group">
        <div class="level-head">
          <h2 class="level-title font-display">{{ levelLabel(lvl) }}</h2>
          <div v-if="slotFor(lvl)" class="level-slots">
            <button
              v-for="n in slotFor(lvl)!.total"
              :key="n"
              type="button"
              class="pip"
              :class="{ 'pip--used': n <= slotFor(lvl)!.used }"
              :aria-label="`Level ${lvl} slot ${n}`"
              @click="n <= slotFor(lvl)!.used ? store.restoreSlot(c.id, lvl) : store.useSlot(c.id, lvl)"
            />
            <span class="level-slots__count tabular">
              {{ slotFor(lvl)!.total - slotFor(lvl)!.used }}/{{ slotFor(lvl)!.total }}
            </span>
          </div>
        </div>

        <div class="spell-grid">
          <v-card
            v-for="sp in spells"
            :key="sp.id"
            class="spell pa-3"
            :class="{ 'spell--unprepared': lvl > 0 && !sp.prepared }"
            color="surface"
          >
            <div class="spell__top">
              <span class="spell__school" :style="{ background: schoolColor[sp.school] }" :title="sp.school" />
              <div class="spell__name">{{ sp.name }}</div>
              <v-spacer />
              <v-tooltip v-if="sp.concentration" text="Concentration" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" size="16" icon="mdi-eye-outline" color="hp-temp" />
                </template>
              </v-tooltip>
              <v-tooltip v-if="sp.ritual" text="Ritual" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" size="16" icon="mdi-book-open-variant" color="secondary" />
                </template>
              </v-tooltip>
            </div>

            <div class="spell__meta">
              <span class="text-capitalize">{{ sp.school }}</span>
              <span class="dot">·</span>{{ sp.castingTime }}
              <span class="dot">·</span>{{ sp.range }}
            </div>
            <p class="spell__desc">{{ sp.description }}</p>

            <div class="spell__foot">
              <span class="spell__comp micro-label">{{ sp.components }} <span class="dot">·</span> {{ sp.duration }}</span>
              <v-spacer />
              <template v-if="lvl === 0">
                <v-chip size="x-small" color="primary" variant="tonal">At will</v-chip>
              </template>
              <template v-else>
                <v-btn
                  size="x-small"
                  variant="text"
                  :color="sp.prepared ? 'primary' : undefined"
                  :prepend-icon="sp.prepared ? 'mdi-check-circle' : 'mdi-circle-outline'"
                  @click="store.toggleSpellPrepared(c.id, sp.id)"
                >
                  {{ sp.prepared ? 'Prepared' : 'Prepare' }}
                </v-btn>
                <v-btn
                  size="x-small"
                  variant="flat"
                  color="secondary"
                  :disabled="!slotFor(lvl) || slotFor(lvl)!.used >= slotFor(lvl)!.total"
                  @click="store.useSlot(c.id, lvl)"
                >
                  Cast
                </v-btn>
              </template>
            </div>
          </v-card>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.noncaster {
  text-align: center;
  padding: 80px 20px;
}
.cast-head {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.cast-stat {
  padding: 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  text-align: center;
}
.cast-stat__value {
  font-size: 1.5rem;
  font-weight: 700;
}
.cast-stat__label {
  font-size: 0.68rem;
  opacity: 0.55;
  margin-top: 2px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.toolbar__search {
  max-width: 320px;
}
.level-group {
  margin-bottom: 24px;
}
.level-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}
.level-title {
  font-size: 1.1rem;
  font-weight: 600;
}
.level-slots {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pip {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 2px solid rgb(var(--v-theme-secondary));
  background: transparent;
  cursor: pointer;
}
.pip--used {
  background: rgb(var(--v-theme-secondary));
}
.level-slots__count {
  font-size: 0.75rem;
  opacity: 0.6;
  margin-left: 4px;
}
.spell-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.spell {
  transition: opacity 0.15s ease;
}
.spell--unprepared {
  opacity: 0.55;
}
.spell__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.spell__school {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}
.spell__name {
  font-weight: 600;
  font-size: 0.98rem;
}
.spell__meta {
  font-size: 0.75rem;
  opacity: 0.6;
  margin: 4px 0 6px;
}
.spell__desc {
  font-size: 0.82rem;
  line-height: 1.5;
  opacity: 0.85;
  margin: 0 0 10px;
}
.spell__foot {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
</style>
