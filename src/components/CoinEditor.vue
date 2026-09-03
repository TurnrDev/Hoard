<script setup lang="ts">
import { computed, reactive, watch } from "vue"
import type { Coins } from "@/types"
import { COIN_COLOR, COIN_LABEL, COIN_ORDER, coinsToGold, formatGold } from "@/lib/money"

const props = defineProps<{ modelValue: Coins }>()
const emit = defineEmits<{ "update:modelValue": [Coins] }>()

// local editable copy so typing feels immediate
const local = reactive<Coins>({ ...props.modelValue })

watch(
  () => props.modelValue,
  (v) => Object.assign(local, v),
)

function commit(key: keyof Coins, raw: number | string) {
  const n = Math.max(0, Math.floor(Number(raw) || 0))
  local[key] = n
  emit("update:modelValue", { ...local })
}

const totalGold = computed(() => coinsToGold(local))
</script>

<template>
  <div class="coin-editor">
    <div class="coin-grid">
      <div v-for="key in COIN_ORDER" :key="key" class="coin">
        <div class="coin__badge" :style="{ '--cc': COIN_COLOR[key] }">{{ key.toUpperCase() }}</div>
        <v-text-field
          :model-value="local[key]"
          type="number"
          min="0"
          density="compact"
          hide-details
          class="coin__input tabular"
          :aria-label="COIN_LABEL[key]"
          @update:model-value="(v) => commit(key, v)"
        />
        <div class="coin__label">{{ COIN_LABEL[key] }}</div>
      </div>
    </div>

    <div class="coin-total">
      <span class="micro-label">Total Value</span>
      <span class="coin-total__value font-display tabular">{{ formatGold(totalGold) }}</span>
    </div>
  </div>
</template>

<style scoped>
.coin-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.coin-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
@media (max-width: 560px) {
  .coin-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.coin {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.coin__badge {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.62rem;
  font-weight: 800;
  color: #0b0e12;
  background: var(--cc);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--cc) 30%, transparent);
}
.coin__input {
  width: 100%;
}
.coin__input :deep(input) {
  text-align: center;
  font-weight: 600;
}
.coin__label {
  font-size: 0.66rem;
  opacity: 0.55;
}
.coin-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 12px;
  background: color-mix(in srgb, rgb(var(--v-theme-primary)) 10%, transparent);
  border: 1px solid color-mix(in srgb, rgb(var(--v-theme-primary)) 30%, transparent);
}
.coin-total__value {
  font-size: 1.4rem;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
}
</style>
