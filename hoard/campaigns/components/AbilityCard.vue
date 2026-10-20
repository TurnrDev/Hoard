<template>
  <article class="border rounded-3 p-3 h-100 text-center">
    <header class="mb-3">
      <h3 class="h5 mb-0">{{ label }}</h3>
      <span class="small text-uppercase text-body-secondary">
        {{ abbreviation }} · {{ displayValue(score) }}
      </span>
    </header>
    <div class="row row-cols-2 g-2 align-items-start tabular-nums">
      <div class="col">
        <span class="small text-body-secondary d-block mb-1">Modifier</span>
        <strong class="fs-3 lh-1">{{ modifier }}</strong>
      </div>
      <div class="col">
        <span class="small text-body-secondary d-block mb-1">Save</span>
        <strong class="fs-3 lh-1">{{ signed(save) }}</strong>
      </div>
    </div>
  </article>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";

type DiceCloudValue = string | number | null;

export default defineComponent({
  props: {
    label: { type: String, required: true },
    abbreviation: { type: String, required: true },
    score: {
      type: [String, Number] as PropType<DiceCloudValue>,
      default: null,
    },
    save: {
      type: [String, Number] as PropType<DiceCloudValue>,
      default: null,
    },
  },
  computed: {
    modifier(): string {
      const score = this.numberValue(this.score);

      if (score === null) {
        return "—";
      }

      return this.signed(Math.floor((score - 10) / 2));
    },
  },
  methods: {
    displayValue(value: DiceCloudValue): string {
      return value === null || value === "" ? "—" : String(value);
    },
    numberValue(value: DiceCloudValue): number | null {
      if (typeof value === "number" && Number.isFinite(value)) {
        return value;
      }

      if (typeof value === "string" && value.trim() !== "") {
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
      }

      return null;
    },
    signed(value: DiceCloudValue | number): string {
      const number = this.numberValue(value);

      if (number === null) {
        return "—";
      }

      return number >= 0 ? `+${number}` : `−${Math.abs(number)}`;
    },
  },
});
</script>
