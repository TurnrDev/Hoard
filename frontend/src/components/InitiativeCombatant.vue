<template>
  <PartyRailEntry
    class="party-rail__entry--combatant"
    :name="displayName"
    :portrait-url="combatant.portrait_url"
    :conditions="combatant.conditions"
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
    <div
      v-if="canManage"
      class="d-grid gap-2 mt-3"
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
  </PartyRailEntry>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { ActingContext } from "../context";
import CombatantVisibilityControls from "./CombatantVisibilityControls.vue";
import ConditionManager from "./ConditionManager.vue";
import PartyRailEntry from "./PartyRailEntry.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: {
    CombatantVisibilityControls,
    ConditionManager,
    PartyRailEntry,
  },
  props: {
    combatant: { type: Object as PropType<PartyRailCombatant>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    connected: { type: Boolean, default: false },
    expanded: { type: Boolean, default: false },
    canManage: { type: Boolean, default: false },
    current: { type: Boolean, default: false },
  },
  emits: ["apply-condition", "remove-condition", "update-visibility"],
  computed: {
    displayName(): string {
      return this.activeContext.kind === "pc" &&
        this.activeContext.character_id === this.combatant.character_id
        ? "You"
        : this.combatant.name;
    },
    showHealthBar(): boolean {
      return Boolean(
        (this.canManage || this.combatant.show_hp_bar) &&
        this.combatant.health_percentage !== null,
      );
    },
    showHealthNumbers(): boolean {
      return Boolean(
        (this.canManage || this.combatant.show_hp_numbers) &&
        this.combatant.current_hp !== null &&
        this.combatant.max_hp !== null,
      );
    },
  },
});
</script>
