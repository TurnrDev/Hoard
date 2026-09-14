<template>
  <li
    class="party-rail__entry party-rail__entry--character"
    :class="`party-rail__entry--${healthState}`"
  >
    <OverlayBadge
      :value="connected ? '✓' : '○'"
      :severity="connected ? 'success' : 'secondary'"
      :aria-label="`${label} — ${connected ? 'Connected' : 'Offline'}`"
    >
      <CharacterAvatar
        class="party-rail__avatar"
        :character="character"
        size="rail"
      />
    </OverlayBadge>
    <div
      v-if="expanded"
      class="party-rail__character-details"
    >
      <span class="party-rail__entry-name">{{ label }}</span>
      <span class="visually-hidden">— {{ connected ? "Connected" : "Offline" }}</span>
      <span class="party-rail__health-label">
        {{ character.sheet.current_hp }} / {{ character.sheet.max_hp }} HP
      </span>
      <ProgressBar
        :value="healthPercentage"
        :show-value="false"
        :aria-label="`${label} health: ${character.sheet.current_hp} of ${character.sheet.max_hp}`"
      />
    </div>
    <ProgressBar
      v-else
      class="party-rail__compact-health"
      :value="healthPercentage"
      :show-value="false"
      :aria-label="`${label} health: ${character.sheet.current_hp} of ${character.sheet.max_hp}`"
    />
  </li>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import OverlayBadge from "primevue/overlaybadge";
import ProgressBar from "primevue/progressbar";
import type { Character } from "../api";
import type { ActingContext } from "../context";
import CharacterAvatar from "./CharacterAvatar.vue";

export default defineComponent({
  components: { CharacterAvatar, OverlayBadge, ProgressBar },
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
    healthState(): "critical" | "wounded" | "healthy" {
      if (this.healthPercentage <= 25) {
        return "critical";
      }

      if (this.healthPercentage <= 60) {
        return "wounded";
      }

      return "healthy";
    },
  },
});
</script>
