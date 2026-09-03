<script setup lang="ts">
import { ABILITY_ORDER, abilityMod, formatMod } from "@/lib/dnd"
import type { Abilities } from "@/types"

defineProps<{ abilities: Abilities }>()
</script>

<template>
  <div class="ability-grid">
    <div v-for="key in ABILITY_ORDER" :key="key" class="ability">
      <div class="ability__key micro-label">{{ key }}</div>
      <div class="ability__mod font-display tabular">{{ formatMod(abilityMod(abilities[key])) }}</div>
      <div class="ability__score tabular">{{ abilities[key] }}</div>
    </div>
  </div>
</template>

<style scoped>
.ability-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}
@media (max-width: 600px) {
  .ability-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.ability {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 4px 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.ability__key {
  opacity: 0.55;
}
.ability__mod {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.2;
}
.ability__score {
  font-size: 0.75rem;
  opacity: 0.6;
}
</style>
