<template>
  <li class="party-rail__entry party-rail__entry--combatant align-items-center">
    <span class="party-rail__initiative tabular-nums">{{ combatant.initiative }}</span>
    <div class="party-rail__combatant-content">
      <span class="party-rail__entry-name d-block text-truncate">
        {{ combatant.name }}
      </span>
      <span
        v-if="expanded && combatant.conditions.length"
        class="party-rail__conditions small"
      >
        {{ conditionSummary }}
      </span>
      <template v-if="hasVisibleHealth">
        <span
          v-if="expanded && combatant.showHpNumbers"
          class="d-block text-truncate small text-body-secondary tabular-nums"
        >
          {{ combatant.currentHp }} / {{ combatant.maxHp }} HP
        </span>
        <ProgressBar
          v-if="combatant.showHpBar"
          :value="healthPercentage"
          :show-value="false"
          :aria-label="healthLabel"
        />
      </template>
      <CombatantVisibilityControls
        v-if="expanded && canManageVisibility && combatant.kind !== 'pc'"
        :combatant="combatant"
        @update-visibility="$emit('update-visibility', $event)"
      />
    </div>
  </li>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import ProgressBar from "primevue/progressbar";
import CombatantVisibilityControls from "./CombatantVisibilityControls.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: { CombatantVisibilityControls, ProgressBar },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
    expanded: { type: Boolean, default: false },
    canManageVisibility: { type: Boolean, default: false },
  },
  emits: ["update-visibility"],
  computed: {
    hasVisibleHealth(): boolean {
      return this.combatant.currentHp !== null && this.combatant.maxHp !== null;
    },
    healthPercentage(): number {
      if (
        !this.hasVisibleHealth ||
        !this.combatant.maxHp ||
        this.combatant.maxHp <= 0
      ) {
        return 0;
      }

      return Math.max(
        0,
        Math.min(100, (this.combatant.currentHp! / this.combatant.maxHp) * 100),
      );
    },
    healthLabel(): string {
      if (!this.hasVisibleHealth) {
        return `${this.combatant.name} health`;
      }

      return this.combatant.showHpNumbers
        ? `${this.combatant.name} health: ${this.combatant.currentHp} of ${this.combatant.maxHp}`
        : `${this.combatant.name} health bar`;
    },
    conditionSummary(): string {
      return this.combatant.conditions
        .map((condition) =>
          condition.exhaustionLevel
            ? `${condition.label} ${condition.exhaustionLevel}`
            : condition.label,
        )
        .join(", ");
    },
  },
});
</script>
