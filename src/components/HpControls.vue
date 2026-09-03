<script setup lang="ts">
import { ref } from "vue"
import { useCampaign } from "@/stores/campaign"

const props = defineProps<{ characterId: string }>()
const store = useCampaign()
const amount = ref<number | null>(null)

function apply(sign: 1 | -1) {
  const v = amount.value
  if (!v || v <= 0) return
  store.applyHpDelta(props.characterId, sign * v)
  amount.value = null
}
function addTemp() {
  const v = amount.value
  if (!v || v <= 0) return
  const c = store.charById(props.characterId)
  store.setTempHp(props.characterId, (c?.tempHp ?? 0) + v)
  amount.value = null
}
</script>

<template>
  <div class="hp-controls">
    <v-text-field
      v-model.number="amount"
      type="number"
      placeholder="0"
      hide-details
      density="comfortable"
      class="hp-controls__input tabular"
      aria-label="HP amount"
    />
    <div class="hp-controls__buttons">
      <v-btn color="hp-danger" variant="flat" size="small" prepend-icon="mdi-sword" @click="apply(-1)">
        Damage
      </v-btn>
      <v-btn color="hp-healthy" variant="flat" size="small" prepend-icon="mdi-heart-plus" @click="apply(1)">
        Heal
      </v-btn>
      <v-btn color="hp-temp" variant="tonal" size="small" prepend-icon="mdi-shield-plus" @click="addTemp">
        Temp
      </v-btn>
    </div>
  </div>
</template>

<style scoped>
.hp-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.hp-controls__input :deep(input) {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 600;
}
.hp-controls__buttons {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}
</style>
