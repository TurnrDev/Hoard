<template>
  <Transition
    name="ability-card-flip"
    mode="out-in"
  >
    <section
      v-if="!calculationVisible"
      key="summary"
      class="border rounded-3 p-3 p-md-4 h-100"
    >
      <header class="d-flex align-items-start justify-content-between gap-2">
        <div class="text-uppercase fw-semibold small text-body-secondary">
          {{ label }}
        </div>
        <div
          v-if="$slots.actions"
          @click.stop
          @keydown.stop
        >
          <slot name="actions" />
        </div>
      </header>

      <div
        class="h4 mt-3 mb-0 tabular-nums"
        :class="{ 'calculation-card__summary--interactive': interactive }"
        :role="interactive ? 'button' : undefined"
        :tabindex="interactive ? 0 : undefined"
        :aria-label="interactive ? activationLabel : undefined"
        @click="activate"
        @keydown.enter="activate"
        @keydown.space.prevent="activate"
      >
        <slot name="summary">{{ summary }}</slot>
      </div>

      <Button
        class="mt-3"
        size="small"
        text
        icon="mdi mdi-rotate-3d-variant"
        label="Show calculation"
        :aria-label="`Show ${label} calculation`"
        @click.stop="showCalculation"
        @keydown.stop
      />
    </section>

    <section
      v-else
      key="calculation"
      class="border rounded-3 p-3 p-md-4 h-100"
    >
      <header class="d-flex align-items-start justify-content-between gap-3 mb-3">
        <div>
          <div class="text-uppercase fw-semibold small text-body-secondary">
            {{ label }}
          </div>
          <span class="small text-body-secondary">Calculation</span>
        </div>
        <Button
          size="small"
          text
          rounded
          icon="mdi mdi-rotate-3d-variant"
          :aria-label="`Show ${label} summary`"
          @click="hideCalculation"
        />
      </header>

      <CalculationBreakdown
        :label="calculationLabel || label"
        :calculation="calculation"
        expanded
      />

      <Button
        class="mt-3"
        size="small"
        text
        icon="mdi mdi-arrow-u-left-top"
        label="Back to summary"
        @click="hideCalculation"
      />
    </section>
  </Transition>
</template>

<script lang="ts">
import Button from "primevue/button";
import { defineComponent, type PropType } from "vue";
import type { Calculation } from "@/api";
import CalculationBreakdown from "./CalculationBreakdown.vue";

export default defineComponent({
  components: { Button, CalculationBreakdown },
  props: {
    label: { type: String, required: true },
    summary: { type: String, required: true },
    calculation: { type: Object as PropType<Calculation>, required: true },
    interactive: { type: Boolean, default: false },
    activationLabel: { type: String, default: "" },
    calculationLabel: { type: String, default: "" },
  },
  emits: ["activate"],
  data() {
    return {
      calculationVisible: false,
    };
  },
  methods: {
    activate(): void {
      if (this.interactive) {
        this.$emit("activate");
      }
    },
    showCalculation(): void {
      this.calculationVisible = true;
    },
    hideCalculation(): void {
      this.calculationVisible = false;
    },
  },
});
</script>

<style scoped>
.calculation-card__summary--interactive {
  cursor: pointer;
}

.ability-card-flip-enter-active,
.ability-card-flip-leave-active {
  transition:
    transform 140ms ease,
    opacity 140ms ease;
  transform-origin: center;
}

.ability-card-flip-enter-from {
  opacity: 0;
  transform: rotateY(90deg);
}

.ability-card-flip-leave-to {
  opacity: 0;
  transform: rotateY(-90deg);
}

@media (prefers-reduced-motion: reduce) {
  .ability-card-flip-enter-active,
  .ability-card-flip-leave-active {
    transition: none;
  }
}
</style>
