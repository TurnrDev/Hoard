<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"
import type { Character } from "@/types"

const props = withDefaults(
  defineProps<{
    orientation?: "vertical" | "horizontal" | "stories"
  }>(),
  { orientation: "vertical" },
)

const store = useCampaign()
const party = computed(() => store.party)

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

// --- stories ring geometry ---
const STORY_SIZE = 58
const STORY_STROKE = 4
const storyRadius = (STORY_SIZE - STORY_STROKE) / 2
const storyCircumference = 2 * Math.PI * storyRadius
const storyCenter = STORY_SIZE / 2
function storyDash(c: Character) {
  const r = Math.max(0, Math.min(1, hpRatio(c)))
  return `${r * storyCircumference} ${storyCircumference}`
}
function storyStroke(c: Character) {
  if (c.hp <= 0) return "#64748b"
  const r = hpRatio(c)
  if (r <= 0.25) return "#f87171"
  if (r <= 0.5) return "#fbbf24"
  return "#34d399"
}
</script>

<template>
  <!-- Instagram-stories-style rail: circular avatar wrapped in an HP ring -->
  <div v-if="orientation === 'stories'" class="stories no-scrollbar">
    <button
      v-for="c in party"
      :key="c.id"
      type="button"
      class="story"
      :class="{ 'story--active': c.id === store.selectedCharacterId, 'story--down': c.hp <= 0 }"
      @click="store.selectCharacter(c.id)"
    >
      <div class="story__ring" :style="{ width: `${STORY_SIZE}px`, height: `${STORY_SIZE}px` }">
        <svg :width="STORY_SIZE" :height="STORY_SIZE" :viewBox="`0 0 ${STORY_SIZE} ${STORY_SIZE}`">
          <circle
            :cx="storyCenter"
            :cy="storyCenter"
            :r="storyRadius"
            fill="none"
            stroke="rgba(255,255,255,0.10)"
            :stroke-width="STORY_STROKE"
          />
          <circle
            :cx="storyCenter"
            :cy="storyCenter"
            :r="storyRadius"
            fill="none"
            :stroke="storyStroke(c)"
            :stroke-width="STORY_STROKE"
            stroke-linecap="round"
            :stroke-dasharray="storyDash(c)"
            :transform="`rotate(-90 ${storyCenter} ${storyCenter})`"
            class="story__arc"
          />
        </svg>
        <div class="story__avatar" :style="{ '--ac': c.avatarColor }">
          <span class="font-display">{{ c.initials }}</span>
        </div>
        <span v-if="c.conditions.length" class="story__cond" :title="c.conditions.join(', ')">
          {{ c.conditions.length }}
        </span>
      </div>
      <div class="story__name">{{ c.name.split(' ')[0] }}</div>
      <div class="story__hp tabular">
        <template v-if="c.hp <= 0">Down</template>
        <template v-else>{{ c.hp }}/{{ c.maxHp }}<span v-if="c.tempHp" class="story__temp"> +{{ c.tempHp }}</span></template>
      </div>
    </button>
  </div>

  <div
    v-else
    class="party-rail no-scrollbar"
    :class="orientation === 'horizontal' ? 'party-rail--h' : 'party-rail--v'"
  >
    <button
      v-for="c in party"
      :key="c.id"
      type="button"
      class="member"
      :class="{ 'member--active': c.id === store.selectedCharacterId, 'member--down': c.hp <= 0 }"
      @click="store.selectCharacter(c.id)"
    >
      <div class="member__avatar" :style="{ '--ac': c.avatarColor }">
        <span class="font-display">{{ c.initials }}</span>
        <span v-if="c.conditions.length" class="member__cond" :title="c.conditions.join(', ')">
          {{ c.conditions.length }}
        </span>
      </div>
      <div class="member__info">
        <div class="member__name">{{ c.name.split(' ')[0] }}</div>
        <div class="member__hpbar">
          <div
            class="member__hpfill"
            :class="`bar-${hpColor(c)}`"
            :style="{ width: `${Math.max(0, hpRatio(c) * 100)}%` }"
          />
        </div>
        <div class="member__hptext tabular">
          <template v-if="c.hp <= 0">Down</template>
          <template v-else>{{ c.hp }}/{{ c.maxHp }}<span v-if="c.tempHp"> +{{ c.tempHp }}</span></template>
        </div>
      </div>
    </button>
  </div>
</template>

<style scoped>
/* --- Instagram-stories rail --- */
.stories {
  display: flex;
  flex-direction: row;
  gap: 14px;
  overflow-x: auto;
  padding: 4px 2px 8px;
}
.story {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 66px;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  color: inherit;
}
.story__ring {
  position: relative;
  display: grid;
  place-items: center;
}
.story__ring svg {
  position: absolute;
  inset: 0;
}
.story__arc {
  transition: stroke-dasharray 0.4s ease, stroke 0.3s ease;
}
.story__avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 0.9rem;
  color: #0b0e12;
  background: var(--ac);
}
.story--active .story__avatar {
  box-shadow: 0 0 0 2px rgb(var(--v-theme-surface)), 0 0 0 4px rgb(var(--v-theme-primary));
}
.story--down {
  opacity: 0.7;
}
.story__cond {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: rgb(var(--v-theme-secondary));
  color: #1e1145;
  font-size: 0.65rem;
  font-weight: 700;
  display: grid;
  place-items: center;
  border: 2px solid rgb(var(--v-theme-surface));
}
.story__name {
  font-weight: 600;
  font-size: 0.75rem;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.story--active .story__name {
  color: rgb(var(--v-theme-primary));
}
.story__hp {
  font-size: 0.65rem;
  opacity: 0.65;
}
.story__temp {
  color: #38bdf8;
}

.party-rail {
  display: flex;
  gap: 8px;
}
.party-rail--v {
  flex-direction: column;
  overflow-y: auto;
}
.party-rail--h {
  flex-direction: row;
  overflow-x: auto;
  padding-bottom: 4px;
}

.member {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.02);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease;
  color: inherit;
}
.party-rail--h .member {
  flex-direction: column;
  min-width: 92px;
  gap: 6px;
}
.member:hover {
  background: rgba(255, 255, 255, 0.05);
}
.member--active {
  border-color: rgb(var(--v-theme-primary));
  background: color-mix(in srgb, rgb(var(--v-theme-primary)) 12%, transparent);
}
.member--down {
  opacity: 0.72;
}

.member__avatar {
  position: relative;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 0.85rem;
  color: #0b0e12;
  background: var(--ac);
}
.member__cond {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: rgb(var(--v-theme-secondary));
  color: #1e1145;
  font-size: 0.65rem;
  font-weight: 700;
  display: grid;
  place-items: center;
  border: 2px solid rgb(var(--v-theme-surface));
}

.member__info {
  min-width: 0;
  flex: 1;
}
.party-rail--h .member__info {
  width: 100%;
  text-align: center;
}
.member__name {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.member__hpbar {
  margin: 4px 0 2px;
  height: 5px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.member__hpfill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.bar-hp-healthy {
  background: #34d399;
}
.bar-hp-wounded {
  background: #fbbf24;
}
.bar-hp-danger {
  background: #f87171;
}
.bar-hp-down {
  background: #64748b;
}
.member__hptext {
  font-size: 0.7rem;
  opacity: 0.7;
}
</style>
