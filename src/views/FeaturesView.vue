<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"
import type { Feature } from "@/types"

const store = useCampaign()
const c = computed(() => store.selected)

const grouped = computed(() => {
  const map = new Map<string, Feature[]>()
  for (const f of c.value.features) {
    if (!map.has(f.source)) map.set(f.source, [])
    map.get(f.source)!.push(f)
  }
  return [...map.entries()]
})

const restColor: Record<string, string> = {
  short: "primary",
  long: "secondary",
  day: "info",
}
</script>

<template>
  <div class="view">
    <header class="head">
      <div>
        <h1 class="head__name font-display">{{ c.name }}</h1>
        <div class="head__sub">{{ c.background }} <span class="dot">·</span> {{ c.alignment }}</div>
      </div>
      <v-btn variant="tonal" color="secondary" prepend-icon="mdi-sleep" @click="store.longRest(c.id)">
        Long Rest
      </v-btn>
    </header>

    <div v-for="[source, feats] in grouped" :key="source" class="group">
      <h2 class="group__title font-display">{{ source }}</h2>
      <div class="feat-grid">
        <v-card v-for="f in feats" :key="f.id" class="feat pa-4" color="surface">
          <div class="feat__head">
            <div class="feat__name">{{ f.name }}</div>
            <v-chip v-if="f.uses" size="x-small" :color="restColor[f.uses.per]" variant="tonal">
              per {{ f.uses.per }} rest
            </v-chip>
          </div>
          <p class="feat__desc">{{ f.description }}</p>

          <div v-if="f.uses" class="feat__uses">
            <div class="uses-pips">
              <button
                v-for="n in f.uses.total"
                :key="n"
                type="button"
                class="upip"
                :class="{ 'upip--used': n <= f.uses.used }"
                :aria-label="`Use ${n}`"
                @click="n <= f.uses!.used ? store.restoreFeature(c.id, f.id) : store.useFeature(c.id, f.id)"
              />
            </div>
            <span class="feat__count tabular">{{ f.uses.total - f.uses.used }}/{{ f.uses.total }} left</span>
          </div>
          <div v-else class="feat__passive micro-label">
            <v-icon size="13" icon="mdi-infinity" class="mr-1" />Always active
          </div>
        </v-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.head__name {
  font-size: 1.6rem;
  font-weight: 700;
}
.head__sub {
  opacity: 0.65;
  font-size: 0.9rem;
}
.group {
  margin-bottom: 24px;
}
.group__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.feat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.feat__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.feat__name {
  font-weight: 600;
  font-size: 1rem;
}
.feat__desc {
  font-size: 0.85rem;
  line-height: 1.5;
  opacity: 0.82;
  margin: 0 0 12px;
}
.feat__uses {
  display: flex;
  align-items: center;
  gap: 10px;
}
.uses-pips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.upip {
  width: 16px;
  height: 16px;
  border-radius: 5px;
  border: 2px solid rgb(var(--v-theme-primary));
  background: transparent;
  cursor: pointer;
}
.upip--used {
  background: rgb(var(--v-theme-primary));
}
.feat__count {
  font-size: 0.75rem;
  opacity: 0.6;
}
.feat__passive {
  display: flex;
  align-items: center;
  opacity: 0.5;
}
.dot {
  opacity: 0.4;
  margin: 0 4px;
}
</style>
