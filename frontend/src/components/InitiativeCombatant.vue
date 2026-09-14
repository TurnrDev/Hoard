<template>
  <li class="party-rail__entry party-rail__entry--combatant align-items-center">
    <span class="party-rail__initiative tabular-nums">{{ combatant.initiative }}</span>
    <div class="party-rail__combatant-content">
      <span class="party-rail__entry-name d-block text-truncate">
        {{ combatant.name }}
      </span>
      <ConditionIndicators
        v-if="combatant.conditions.length"
        :combatant-name="combatant.name"
        :conditions="combatant.conditions"
        :expanded="expanded"
      />
      <template v-if="hasVisibleHealth">
        <span
          v-if="expanded && (canManage || combatant.show_hp_numbers)"
          class="d-block text-truncate small text-body-secondary tabular-nums"
        >
          {{ combatant.current_hp }} / {{ combatant.max_hp }} HP
        </span>
        <ProgressBar
          v-if="canManage || combatant.show_hp_bar"
          :value="healthPercentage"
          :show-value="false"
          :aria-label="healthLabel"
        />
      </template>
      <div
        v-if="expanded && canManage"
        class="d-grid gap-2 mt-2"
      >
        <ConditionManager
          :conditions="combatant.conditions"
          :target-name="combatant.name"
          :target-id="`combatant-${combatant.id}`"
          can-edit
          trigger-only
          @apply="$emit('apply-condition', $event)"
          @remove="$emit('remove-condition', $event)"
        />
        <CombatantVisibilityControls
          v-if="!combatant.is_player_character"
          :combatant="combatant"
          @update-visibility="$emit('update-visibility', $event)"
        />
      </div>
    </div>
  </li>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import ProgressBar from "primevue/progressbar";
import CombatantVisibilityControls from "./CombatantVisibilityControls.vue";
import ConditionIndicators from "./ConditionIndicators.vue";
import ConditionManager from "./ConditionManager.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: {
    CombatantVisibilityControls,
    ConditionIndicators,
    ConditionManager,
    ProgressBar,
  },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
    expanded: { type: Boolean, default: false },
    canManage: { type: Boolean, default: false },
  },
  emits: ["apply-condition", "remove-condition", "update-visibility"],
  computed: {
    hasVisibleHealth(): boolean {
      return this.combatant.current_hp !== null && this.combatant.max_hp !== null;
    },
    healthPercentage(): number {
      if (
        !this.hasVisibleHealth ||
        !this.combatant.max_hp ||
        this.combatant.max_hp <= 0
      ) {
        return 0;
      }

      return Math.max(
        0,
        Math.min(100, (this.combatant.current_hp! / this.combatant.max_hp) * 100),
      );
    },
    healthLabel(): string {
      if (!this.hasVisibleHealth) {
        return `${this.combatant.name} health`;
      }

      return this.canManage || this.combatant.show_hp_numbers
        ? `${this.combatant.name} health: ${this.combatant.current_hp} of ${this.combatant.max_hp}`
        : `${this.combatant.name} health bar`;
    },
  },
});
</script>
