<template>
  <MeterGroup
    :class="{ 'health-bar--compact': compact }"
    class="health-bar"
    :value="meters"
    :max="displayMaximum"
    label-position="end"
    :pt="{ root: { 'aria-label': accessibleLabel } }"
  >
    <template #label>
      <ul
        v-if="showLabels && !compact && hasDetailedValues"
        class="health-bar__labels list-unstyled d-flex flex-wrap gap-3 mb-0 mt-2 small tabular-nums"
      >
        <li>
          <span
            class="mdi mdi-heart-outline"
            aria-hidden="true"
          />
          HP {{ current }} / {{ maximum }}
        </li>
        <li v-if="temporary > 0">
          <span
            class="mdi mdi-shield-plus-outline"
            aria-hidden="true"
          />
          Temporary HP +{{ temporary }}
        </li>
      </ul>
      <span
        v-else
        class="visually-hidden"
      >
        {{ accessibleLabel }}
      </span>
    </template>
  </MeterGroup>
</template>

<script lang="ts">
import MeterGroup from "primevue/metergroup";
import { defineComponent, type PropType } from "vue";

export default defineComponent({
  components: { MeterGroup },
  props: {
    current: { type: Number as PropType<number | null>, default: null },
    maximum: { type: Number as PropType<number | null>, default: null },
    percentage: { type: Number as PropType<number | null>, default: null },
    label: { type: String, default: "Health status" },
    temporary: { type: Number, default: 0 },
    compact: { type: Boolean, default: false },
    showLabels: { type: Boolean, default: false },
  },
  computed: {
    hasDetailedValues(): boolean {
      return this.current !== null && this.maximum !== null && this.maximum > 0;
    },
    currentHitPoints(): number {
      return this.current ?? 0;
    },
    maximumHitPoints(): number {
      return this.maximum ?? 0;
    },
    displayMaximum(): number {
      if (!this.hasDetailedValues) {
        return 100;
      }

      return Math.max(this.maximumHitPoints, this.currentHitPoints + this.temporary);
    },
    healthPercentage(): number {
      if (this.hasDetailedValues) {
        return (this.currentHitPoints / this.maximumHitPoints) * 100;
      }

      return Math.max(0, Math.min(this.percentage ?? 0, 100));
    },
    healthColor(): string {
      const healthPercentage = this.healthPercentage;

      if (healthPercentage <= 25) {
        return "var(--hoard-health-critical)";
      }

      if (healthPercentage <= 60) {
        return "var(--hoard-health-wounded)";
      }

      return "var(--hoard-health-healthy)";
    },
    meters(): Array<{ label: string; value: number; color: string }> {
      const values = [
        {
          label: this.hasDetailedValues ? "Hit points" : "Health status",
          value: this.hasDetailedValues ? this.currentHitPoints : this.healthPercentage,
          color: this.healthColor,
        },
      ];

      if (this.hasDetailedValues && this.temporary > 0) {
        values.push({
          label: "Temporary hit points",
          value: this.temporary,
          color: "var(--hoard-health-temporary)",
        });
      }

      return values;
    },
    accessibleLabel(): string {
      if (!this.hasDetailedValues) {
        return this.label;
      }

      if (this.temporary > 0) {
        return `${this.current} of ${this.maximum} hit points, plus ${this.temporary} temporary hit points`;
      }

      return `${this.current} of ${this.maximum} hit points`;
    },
  },
});
</script>

<style scoped>
.health-bar :deep(.p-metergroup-meters) {
  min-height: 0.75rem;
}

.health-bar--compact :deep(.p-metergroup-meters) {
  min-height: 0.5rem;
}

.health-bar__labels {
  color: var(--p-text-muted-color);
}
</style>
