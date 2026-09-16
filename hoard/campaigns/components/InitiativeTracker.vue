<template>
  <section
    class="party-rail__group"
    aria-labelledby="initiative-heading"
  >
    <h3
      id="initiative-heading"
      class="visually-hidden"
    >
      Initiative
    </h3>
    <ol
      class="party-rail__entries d-flex list-unstyled mb-0"
      :class="expanded ? 'flex-column' : 'flex-row flex-lg-column'"
    >
      <InitiativeCombatant
        v-for="combatant in orderedCombatants"
        :key="combatant.id"
        :combatant="combatant"
        :active-context="activeContext"
        :expanded="expanded"
        :can-view-hidden-health="canViewHiddenHealth"
        :current="combatant.id === currentCombatantId"
      />
    </ol>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { EncounterCombatant } from "@/api";
import type { ActingContext } from "@/campaigns/context";
import InitiativeCombatant from "./InitiativeCombatant.vue";

export default defineComponent({
  components: { InitiativeCombatant },
  props: {
    combatants: { type: Array as PropType<EncounterCombatant[]>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
    canViewHiddenHealth: { type: Boolean, default: false },
    currentCombatantId: {
      type: Number as PropType<number | null>,
      default: null,
    },
  },
  computed: {
    orderedCombatants(): EncounterCombatant[] {
      return [...this.combatants].sort((left, right) => left.position - right.position);
    },
  },
});
</script>
