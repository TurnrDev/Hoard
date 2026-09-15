<template>
  <PartyRailEntry
    class="party-rail__entry--character"
    :name="label"
    :portrait-url="character.portrait_url"
    :conditions="character.conditions"
    :inspired="character.has_inspiration"
    :connected="connected"
    show-presence
    :expanded="expanded"
    :current-hp="character.sheet.current_hp"
    :max-hp="character.sheet.max_hp"
    :health-percentage="healthPercentage"
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
    healthPercentage(): number {
      if (this.character.sheet.max_hp <= 0) {
        return 0;
      }

      return Math.max(
        0,
        Math.min(
          100,
          (this.character.sheet.current_hp / this.character.sheet.max_hp) * 100,
        ),
      );
    },
  },
});
</script>
