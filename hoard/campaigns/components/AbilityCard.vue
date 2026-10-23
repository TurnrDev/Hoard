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
        <span class="d-inline-flex align-items-center gap-1">
          <span
            v-if="proficiencyIcon"
            :class="['mdi', proficiencyIcon, proficiencyClass]"
            role="img"
            :aria-label="proficiencyLabel"
            :title="proficiencyLabel"
          />
          <strong
            class="fs-3 lh-1"
            :class="proficiencyClass"
          >
            {{ signed(save?.value ?? null) }}
          </strong>
        </span>
      </div>
    </div>
  </article>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { DiceCloudSave } from "@/api";

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
      type: Object as PropType<DiceCloudSave | null>,
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
    proficiencyIcon(): string | null {
      const proficiency = this.save?.proficiency;

      if (proficiency === null || proficiency === undefined || proficiency <= 0) {
        return null;
      }

      return proficiency < 1 ? "mdi-shield-half-full" : "mdi-shield-check";
    },
    proficiencyLabel(): string {
      const proficiency = this.save?.proficiency;

      if (proficiency === null || proficiency === undefined || proficiency <= 0) {
        return "No proficiency";
      }

      if (proficiency < 1) {
        return "Partial proficiency";
      }

      if (proficiency > 1) {
        return "Expertise";
      }

      return "Proficient";
    },
    proficiencyClass(): string | undefined {
      const proficiency = this.save?.proficiency;

      if (proficiency === null || proficiency === undefined || proficiency <= 0) {
        return undefined;
      }

      if (proficiency < 1) {
        return "proficiency-bonus proficiency-bonus--half";
      }

      if (proficiency > 1) {
        return "proficiency-bonus proficiency-bonus--expertise";
      }

      return "proficiency-bonus";
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
