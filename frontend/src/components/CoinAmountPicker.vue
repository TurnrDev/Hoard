<script setup lang="ts">
import { computed } from "vue";
import { formatGoldValue } from "../money";

const props = defineProps<{ modelValue: Record<string, number> }>();
const emit = defineEmits<{ "update:modelValue": [amounts: Record<string, number>] }>();
const denominations = ["pp", "gp", "ep", "sp", "cp"];
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
  <div class="text-overline mb-2">Coins</div>
  <v-row
    dense
    class="coin-inputs mb-3"
  >
    <v-col
      v-for="denomination in denominations"
      :key="denomination"
      cols="4"
      sm="4"
    >
      <v-text-field
        :model-value="modelValue[denomination]"
        type="number"
        min="0"
        step="1"
        :label="denomination.toUpperCase()"
        hide-details
        @update:model-value="update(denomination, Number($event))"
      />
    </v-col>
  </v-row>
  <div class="coin-total mb-4">
    <span>Total</span>
    <strong>{{ formatGoldValue(totalValue) }} ¤</strong>
  </div>
</template>
