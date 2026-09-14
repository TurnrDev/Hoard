<template>
  <section class="party-rail__group">
    <ul class="party-rail__entries list-unstyled mb-0">
      <PartyRailMember
        v-for="character in playerCharacters"
        :key="character.id"
        :character="character"
        :active-context="activeContext"
        :connected="connectedFor(character)"
        :expanded="expanded"
      />
    </ul>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { CampaignMember, Character } from "../api";
import type { ActingContext } from "../context";
import PartyRailMember from "./PartyRailMember.vue";

export default defineComponent({
  components: { PartyRailMember },
  props: {
    characters: { type: Array as PropType<Character[]>, required: true },
    members: { type: Array as PropType<CampaignMember[]>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
  },
  computed: {
    playerCharacters(): Character[] {
      return this.characters
        .filter((character) => character.is_active && character.is_player_character)
        .sort((first, second) => {
          const presenceDifference =
            Number(this.connectedFor(second)) - Number(this.connectedFor(first));

          return presenceDifference || first.name.localeCompare(second.name);
        });
    },
  },
  methods: {
    connectedFor(character: Character): boolean {
      return Boolean(
        this.members.find((member) => member.id === character.context_id)?.connected,
      );
    },
  },
});
</script>
