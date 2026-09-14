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
        :connected="combatantConnected(combatant)"
        :expanded="expanded"
        :can-manage="canManage"
        :current="combatant.id === currentCombatantId"
        @apply-condition="$emit('apply-condition', combatant.id, $event)"
        @remove-condition="$emit('remove-condition', combatant.id, $event)"
        @update-visibility="$emit('update-visibility', $event)"
      />
    </ol>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { CampaignMember, Character } from "../api";
import type { ActingContext } from "../context";
import InitiativeCombatant from "./InitiativeCombatant.vue";
import type { PartyRailCombatant } from "./partyRailTypes";

export default defineComponent({
  components: { InitiativeCombatant },
  props: {
    combatants: { type: Array as PropType<PartyRailCombatant[]>, required: true },
    characters: { type: Array as PropType<Character[]>, required: true },
    members: { type: Array as PropType<CampaignMember[]>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
    canManage: { type: Boolean, default: false },
    currentCombatantId: {
      type: Number as PropType<number | null>,
      default: null,
    },
  },
  emits: ["apply-condition", "remove-condition", "update-visibility"],
  computed: {
    orderedCombatants(): PartyRailCombatant[] {
      return [...this.combatants].sort(
        (first, second) => second.initiative - first.initiative,
      );
    },
  },
  methods: {
    combatantConnected(combatant: PartyRailCombatant): boolean {
      if (combatant.character_id === null) {
        return false;
      }

      const character = this.characters.find(
        (candidate) => candidate.id === combatant.character_id,
      );

      if (!character?.context_id) {
        return false;
      }

      return Boolean(
        this.members.find((member) => member.id === character.context_id)?.connected,
      );
    },
  },
});
</script>
