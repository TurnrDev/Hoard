<template>
  <PartyRailEntry
    class="party-rail__entry--combatant"
    :name="displayName"
    :portrait-url="combatant.portrait_url"
    :expanded="expanded"
    :current-hp="showHealthNumbers ? combatant.current_hp : null"
    :max-hp="showHealthNumbers ? combatant.max_hp : null"
    :health-percentage="combatant.health_percentage"
    :current="current"
  >
    <p
      v-if="isOwnedCombatant && combatant.initiative_roll !== null"
      class="small tabular-nums mb-2"
    >
      Initiative
      <strong>{{ combatant.initiative }}</strong>
      <span class="text-body-secondary">
        ({{ combatant.initiative_roll }} {{ signedModifier }})
      </span>
    </p>
  </PartyRailEntry>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { EncounterCombatant } from "@/api";
import type { ActingContext } from "@/campaigns/context";
import PartyRailEntry from "./PartyRailEntry.vue";

export default defineComponent({
  components: { PartyRailEntry },
  props: {
    combatant: { type: Object as PropType<EncounterCombatant>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
    canViewHiddenHealth: { type: Boolean, default: false },
    current: { type: Boolean, default: false },
  },
  computed: {
    signedModifier(): string {
      const modifier = this.combatant.initiative_modifier;

      return modifier >= 0 ? `+ ${modifier}` : `− ${Math.abs(modifier)}`;
    },
    displayName(): string {
      return this.isOwnedCombatant ? "You" : this.combatant.name;
    },
    isOwnedCombatant(): boolean {
      return (
        this.activeContext.kind === "pc" &&
        this.activeContext.character_id === this.combatant.character_id
      );
    },
    showHealthNumbers(): boolean {
      return this.canViewHiddenHealth || this.combatant.show_hp_numbers;
    },
  },
});
</script>
