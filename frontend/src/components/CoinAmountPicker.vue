<script setup lang="ts">
import { computed } from "vue";
import { formatGoldValue } from "../money";

const props = defineProps<{ modelValue: Record<string, number> }>();
const emit = defineEmits<{ "update:modelValue": [amounts: Record<string, number>] }>();
const denominations = [
  { key: "pp", label: "PP", name: "Platinum pieces" },
  { key: "gp", label: "GP", name: "Gold pieces" },
  { key: "ep", label: "EP", name: "Electrum pieces" },
  { key: "sp", label: "SP", name: "Silver pieces" },
  { key: "cp", label: "CP", name: "Copper pieces" },
];
const totalValue = computed(
  () =>
    (props.modelValue.pp ?? 0) * 10 +
    (props.modelValue.gp ?? 0) +
    (props.modelValue.ep ?? 0) / 2 +
    (props.modelValue.sp ?? 0) / 10 +
    (props.modelValue.cp ?? 0) / 100,
);

function update(denomination: string, value: number | null): void {
  emit("update:modelValue", { ...props.modelValue, [denomination]: value ?? 0 });
}
</script>

<template>
  <div class="text-overline mb-1">Coins</div>
  <div class="coin-input-grid mb-3">
    <v-number-input
      v-for="denomination in denominations"
      :key="denomination.key"
      :model-value="modelValue[denomination.key]"
      control-variant="split"
      :min="0"
      :step="1"
      :label="denomination.label"
      :aria-label="denomination.name"
      hide-details
      @update:model-value="update(denomination.key, $event)"
    />
  </div>
  <div class="coin-total mb-4">
    <span>Total</span>
    <strong>{{ formatGoldValue(totalValue) }} ¤</strong>
  </div>
</template>
