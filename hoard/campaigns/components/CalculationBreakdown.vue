<template>
  <dl
    v-if="expanded"
    class="mb-0 small"
  >
    <dt
      v-if="label"
      class="text-body-secondary"
    >
      {{ label }}
    </dt>
    <dd class="fw-semibold mb-1">
      {{ calculation.formula ?? calculation.value }}
    </dd>
    <dd
      v-if="calculation.numeric_formula"
      class="mb-2 text-body-secondary"
    >
      {{ calculation.numeric_formula }}
    </dd>
    <dd
      v-for="component in calculation.components"
      :key="component.label"
      class="mb-1"
    >
      <span class="text-body-secondary">{{ component.label }}:</span>
      {{ component.formula ?? component.value }}
      <Chip
        v-if="component.source === 'override'"
        label="Override"
        class="ms-1"
      />
    </dd>
  </dl>
  <details
    v-else
    class="d-inline-block position-relative"
  >
    <summary
      class="link-body-emphasis text-decoration-underline text-decoration-style-dotted"
    >
      {{ activatorLabel ?? calculation.formula ?? calculation.value }}
      <span
        class="mdi mdi-calculator-variant-outline"
        aria-hidden="true"
      />
    </summary>
    <section
      class="position-absolute end-0 z-3 mt-2 p-3 border rounded-3 bg-body shadow"
      style="min-width: 17.5rem"
    >
      <h3 class="h6">{{ label ?? "Calculation" }}</h3>
      <CalculationBreakdown
        :calculation="calculation"
        :label="label"
        expanded
      />
    </section>
  </details>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Chip from "primevue/chip";
import type { Calculation } from "@/api";

export default defineComponent({
  name: "CalculationBreakdown",
  components: { Chip },
  props: {
    calculation: { type: Object as PropType<Calculation>, required: true },
    label: { type: String, required: false },
    expanded: { type: Boolean, default: false },
    activatorLabel: { type: String, required: false },
  },
});
</script>
