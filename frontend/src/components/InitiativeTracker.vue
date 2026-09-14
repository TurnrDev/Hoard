<template>
  <section
    class="party-rail__group"
    aria-labelledby="initiative-heading"
  >
    <h3
      id="initiative-heading"
      class="party-rail__group-title"
    >
      Initiative
    </h3>
    <ol class="party-rail__entries list-unstyled mb-0">
      <InitiativeCombatant
        v-for="combatant in orderedCombatants"
        :key="combatant.id"
        :combatant="combatant"
        :expanded="expanded"
        :can-manage-visibility="canManageVisibility"
        @update-visibility="$emit('update-visibility', $event)"
      />
    </ol>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import InitiativeCombatant from "./InitiativeCombatant.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: { InitiativeCombatant },
  props: {
    combatants: { type: Array as PropType<PartyRailCombatant[]>, required: true },
    expanded: { type: Boolean, default: false },
    canManageVisibility: { type: Boolean, default: false },
  },
  emits: ["update-visibility"],
  computed: {
    orderedCombatants(): PartyRailCombatant[] {
      return [...this.combatants].sort(
        (first, second) => second.initiative - first.initiative,
      );
    },
  },
});
</script>
