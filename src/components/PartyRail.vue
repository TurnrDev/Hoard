<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"
import type { Character } from "@/types"

const props = withDefaults(
  defineProps<{
    orientation?: "vertical" | "horizontal"
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
</script>

<template>
  <div
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
