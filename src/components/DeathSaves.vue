<script setup lang="ts">
import { computed } from "vue"
import { useCampaign } from "@/stores/campaign"

const props = defineProps<{ characterId: string }>()
const store = useCampaign()
const c = computed(() => store.charById(props.characterId)!)

const successes = computed(() => c.value.deathSaves.successes)
const failures = computed(() => c.value.deathSaves.failures)

const stabilized = computed(() => successes.value >= 3)
const dead = computed(() => failures.value >= 3)

const statusText = computed(() => {
  if (dead.value) return "Dead"
  if (stabilized.value) return "Stabilized"
  return "Unconscious · Dying"
})

// Clicking a pip sets the count to that pip (or clears it if it's the last filled one).
function setSave(kind: "successes" | "failures", pip: number) {
  const current = kind === "successes" ? successes.value : failures.value
  store.setDeathSave(props.characterId, kind, current === pip ? pip - 1 : pip)
}
</script>

<template>
  <div class="death">
    <div class="death__head">
      <v-icon icon="mdi-skull" size="20" :color="dead ? 'error' : 'warning'" />
      <div>
        <div class="death__title font-display">Death Saving Throws</div>
        <div
          class="death__status micro-label"
          :class="{ 'text-success': stabilized, 'text-error': dead }"
        >
          {{ statusText }}
        </div>
      </div>
    </div>

    <div class="death__rows">
      <div class="death__row">
        <span class="death__label">
          <v-icon icon="mdi-heart-pulse" size="16" color="success" class="mr-1" />
          Successes
        </span>
        <div class="pips">
          <button
            v-for="n in 3"
            :key="`s${n}`"
            type="button"
            class="pip pip--success"
            :class="{ 'pip--on': n <= successes }"
            :aria-label="`Success ${n}`"
            @click="setSave('successes', n)"
          />
        </div>
      </div>

      <div class="death__row">
        <span class="death__label">
          <v-icon icon="mdi-skull-outline" size="16" color="error" class="mr-1" />
          Failures
        </span>
        <div class="pips">
          <button
            v-for="n in 3"
            :key="`f${n}`"
            type="button"
            class="pip pip--fail"
            :class="{ 'pip--on': n <= failures }"
            :aria-label="`Failure ${n}`"
            @click="setSave('failures', n)"
          />
        </div>
      </div>
    </div>

    <div class="death__actions">
      <v-btn
        variant="tonal"
        color="success"
        size="small"
        prepend-icon="mdi-shield-plus"
        @click="store.stabilize(characterId)"
      >
        Stabilize
      </v-btn>
      <v-btn
        variant="text"
        size="small"
        prepend-icon="mdi-restore"
        @click="store.resetDeathSaves(characterId)"
      >
        Reset
      </v-btn>
    </div>

    <v-divider class="my-3" />
    <div class="death__hint">
      Bring {{ c.name.split(" ")[0] }} back with any healing, or use the HP controls after they regain consciousness.
    </div>
    <v-btn
      color="success"
      variant="flat"
      size="small"
      block
      prepend-icon="mdi-heart-plus"
      class="mt-2"
      @click="store.applyHpDelta(characterId, 1); store.resetDeathSaves(characterId)"
    >
      Revive at 1 HP
    </v-btn>
  </div>
</template>

<style scoped>
.death {
  display: flex;
  flex-direction: column;
  width: 100%;
}
.death__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.death__title {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.1;
}
.death__status {
  margin-top: 2px;
}
.death__rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.death__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.death__label {
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 600;
}
.pips {
  display: flex;
  gap: 8px;
}
.pip {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.25);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pip--success.pip--on {
  background: rgb(var(--v-theme-success));
  border-color: rgb(var(--v-theme-success));
  box-shadow: 0 0 8px rgba(var(--v-theme-success), 0.5);
}
.pip--fail.pip--on {
  background: rgb(var(--v-theme-error));
  border-color: rgb(var(--v-theme-error));
  box-shadow: 0 0 8px rgba(var(--v-theme-error), 0.5);
}
.death__actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.death__hint {
  font-size: 0.75rem;
  opacity: 0.6;
  line-height: 1.4;
}
</style>
