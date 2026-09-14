<template>
  <PartyRailEntry
    class="party-rail__entry--combatant"
    :name="displayName"
    :portrait-url="combatant.portrait_url"
    :conditions="combatant.conditions"
    :inspired="combatant.has_inspiration"
    :connected="connected"
    :show-presence="combatant.is_player_character"
    :expanded="expanded"
    :current-hp="combatant.current_hp"
    :max-hp="combatant.max_hp"
    :health-percentage="combatant.health_percentage"
    :show-hp-bar="showHealthBar"
    :show-hp-numbers="showHealthNumbers"
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
import type { ActingContext } from "../context";
import PartyRailEntry from "./PartyRailEntry.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: {
    PartyRailEntry,
  },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    connected: { type: Boolean, default: false },
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
    showHealthBar(): boolean {
      return Boolean(
        (this.canViewHiddenHealth || this.combatant.show_hp_bar) &&
        this.combatant.health_percentage !== null,
      );
    },
    showHealthNumbers(): boolean {
      return Boolean(
        (this.canViewHiddenHealth || this.combatant.show_hp_numbers) &&
        this.combatant.current_hp !== null &&
        this.combatant.max_hp !== null,
      );
    },
  },
});
</script>
