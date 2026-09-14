<template>
  <fieldset>
    <legend class="fs-6 fw-semibold">Coins</legend>
    <div class="row g-2">
      <label
        class="col-6 col-md"
        v-for="denomination in denominations"
        :key="denomination.key"
      >
        <span class="small fw-semibold">{{ denomination.label }}</span>
        <InputNumber
          :model-value="modelValue[denomination.key]"
          :min="0"
          :step="1"
          :aria-label="denomination.name"
          fluid
          @update:model-value="update(denomination.key, $event)"
        />
      </label>
    </div>
    <p class="d-flex justify-content-between border-top mt-3 pt-3 mb-0">
      <span class="text-body-secondary">Total</span>
      <strong class="tabular-nums">{{ formatGoldValue(totalValue) }} ¤</strong>
    </p>
  </fieldset>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import InputNumber from "primevue/inputnumber";
import { formatGoldValue } from "../money";

export default defineComponent({
  components: { InputNumber },
  props: {
    modelValue: { type: Object as PropType<Record<string, number>>, required: true },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      denominations: [
        { key: "pp", label: "PP", name: "Platinum pieces" },
        { key: "gp", label: "GP", name: "Gold pieces" },
        { key: "ep", label: "EP", name: "Electrum pieces" },
        { key: "sp", label: "SP", name: "Silver pieces" },
        { key: "cp", label: "CP", name: "Copper pieces" },
      ],
    };
  },
  computed: {
    totalValue(): number {
      return (
        (this.modelValue.pp ?? 0) * 10 +
        (this.modelValue.gp ?? 0) +
        (this.modelValue.ep ?? 0) / 2 +
        (this.modelValue.sp ?? 0) / 10 +
        (this.modelValue.cp ?? 0) / 100
      );
    },
  },
  methods: {
    formatGoldValue,
    update(denomination: string, value: number | null): void {
      this.$emit("update:modelValue", {
        ...this.modelValue,
        [denomination]: value ?? 0,
      });
    },
  },
});
</script>
