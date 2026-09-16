<template>
  <PartyRailEntry
    class="party-rail__entry--character"
    :name="label"
    :portrait-url="character.portrait_url"
    :connected="connected"
    show-presence
    :expanded="expanded"
  />
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { Character } from "@/api";
import type { ActingContext } from "@/campaigns/context";
import PartyRailEntry from "./PartyRailEntry.vue";

export default defineComponent({
  components: { PartyRailEntry },
  props: {
    character: { type: Object as PropType<Character>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
    connected: { type: Boolean, default: false },
  },
  computed: {
    isCurrentCharacter(): boolean {
      return (
        this.activeContext.kind === "pc" &&
        this.activeContext.character_id === this.character.id
      );
    },
    label(): string {
      return this.isCurrentCharacter ? "You" : this.character.name;
    },
  },
});
</script>
