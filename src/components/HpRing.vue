<script setup lang="ts">
import { computed } from "vue"

const props = withDefaults(
  defineProps<{
    hp: number
    maxHp: number
    tempHp?: number
    size?: number
    stroke?: number
    label?: boolean
  }>(),
  { tempHp: 0, size: 132, stroke: 10, label: true },
)

const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const ratio = computed(() => (props.maxHp > 0 ? Math.max(0, Math.min(1, props.hp / props.maxHp)) : 0))
const tempRatio = computed(() =>
  props.maxHp > 0 ? Math.max(0, Math.min(1, (props.tempHp ?? 0) / props.maxHp)) : 0,
)

const dashHp = computed(() => `${ratio.value * circumference.value} ${circumference.value}`)
const dashTemp = computed(() => `${tempRatio.value * circumference.value} ${circumference.value}`)

const hpColor = computed(() => {
  if (props.hp <= 0) return "var(--hp-down)"
  if (ratio.value <= 0.25) return "var(--hp-danger)"
  if (ratio.value <= 0.5) return "var(--hp-wounded)"
  return "var(--hp-healthy)"
})

// hp semantic vars resolved from Vuetify theme colors
const cssVars = computed(() => ({
  "--hp-healthy": "#34d399",
  "--hp-wounded": "#fbbf24",
  "--hp-danger": "#f87171",
  "--hp-down": "#64748b",
  "--hp-temp": "#38bdf8",
}))

const center = computed(() => props.size / 2)
const down = computed(() => props.hp <= 0)
</script>

<template>
  <div class="hp-ring" :style="{ width: `${size}px`, height: `${size}px`, ...cssVars }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        stroke="rgba(255,255,255,0.08)"
        :stroke-width="stroke"
      />
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke="hpColor"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="dashHp"
        :transform="`rotate(-90 ${center} ${center})`"
        class="ring-value"
      />
      <circle
        v-if="tempHp && tempHp > 0"
        :cx="center"
        :cy="center"
        :r="radius - stroke - 2"
        fill="none"
        stroke="var(--hp-temp)"
        :stroke-width="Math.max(3, stroke - 4)"
        stroke-linecap="round"
        :stroke-dasharray="dashTemp"
        :transform="`rotate(-90 ${center} ${center})`"
        class="ring-value"
      />
    </svg>
    <div v-if="label" class="hp-ring__label">
      <template v-if="down">
        <span class="hp-ring__down">DOWN</span>
      </template>
      <template v-else>
        <span class="hp-ring__hp tabular">{{ hp }}</span>
        <span class="hp-ring__max tabular">/ {{ maxHp }}</span>
        <span v-if="tempHp && tempHp > 0" class="hp-ring__temp tabular">+{{ tempHp }} temp</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.hp-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ring-value {
  transition: stroke-dasharray 0.4s ease, stroke 0.3s ease;
}
.hp-ring__label {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  line-height: 1.05;
}
.hp-ring__hp {
  font-size: 1.75rem;
  font-weight: 700;
}
.hp-ring__max {
  font-size: 0.8rem;
  opacity: 0.6;
}
.hp-ring__temp {
  margin-top: 2px;
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--hp-temp);
}
.hp-ring__down {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--hp-danger);
}
</style>
