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
      </header>

      <Skeleton
        class="mt-3"
        width="4.5rem"
        height="1.75rem"
      />

      <Button
        class="mt-3"
        size="small"
        text
        icon="mdi mdi-rotate-3d-variant"
        label="Show calculation"
        :aria-label="`Show ${label} calculation`"
        @click.stop="showCalculation"
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

      <div class="d-grid gap-2">
        <Skeleton width="70%" />
        <Skeleton width="90%" />
        <Skeleton width="55%" />
      </div>

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
import Skeleton from "primevue/skeleton";
import { defineComponent } from "vue";

export default defineComponent({
  name: "CalculationCard",
  components: { Button, Skeleton },
  props: {
    label: { type: String, required: true },
  },
  data() {
    return {
      calculationVisible: false,
    };
  },
  methods: {
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
