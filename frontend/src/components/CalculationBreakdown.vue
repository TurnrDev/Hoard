<script setup lang="ts">
import type { Calculation } from "../api";

defineProps<{
  calculation: Calculation;
  label?: string;
  expanded?: boolean;
  activatorLabel?: string;
}>();
</script>

<template>
  <div
    v-if="expanded"
    class="calculation-breakdown"
  >
    <div class="text-caption text-medium-emphasis">{{ label }}</div>
    <div class="font-weight-medium">{{ calculation.formula ?? calculation.value }}</div>
    <div
      v-for="component in calculation.components"
      :key="component.label"
      class="text-caption"
    >
      {{ component.label }}: {{ component.formula ?? component.value }}
      <v-chip
        v-if="component.source === 'override'"
        size="x-small"
        color="warning"
      >
        Override
      </v-chip>
    </div>
  </div>
  <v-menu
    v-else
    open-on-hover
    open-on-click
    :close-on-content-click="false"
  >
    <template #activator="{ props }">
      <button
        v-bind="props"
        type="button"
        class="calculation-compact"
        @click.stop
        @keydown.stop
      >
        {{ activatorLabel ?? calculation.formula ?? calculation.value }}
        <v-icon size="x-small">mdi-calculator-variant-outline</v-icon>
      </button>
    </template>
    <v-card
      class="pa-3"
      min-width="280"
    >
      <div class="text-subtitle-2 mb-2">{{ label ?? "Calculation" }}</div>
      <CalculationBreakdown
        :calculation="calculation"
        :label="label"
        expanded
      />
    </v-card>
  </v-menu>
</template>

<style scoped>
.calculation-compact {
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  cursor: pointer;
  font: inherit;
  padding: 0;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
}
</style>
