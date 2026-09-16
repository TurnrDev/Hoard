<template>
  <li
    class="party-rail__entry align-items-center"
    :class="`party-rail__entry--${healthState}`"
    :aria-current="current ? 'step' : undefined"
  >
    <OverlayBadge
      v-if="showPresence"
      :value="connected ? '✓' : '○'"
      :severity="connected ? 'success' : 'secondary'"
      :aria-label="`${name} — ${connected ? 'Connected' : 'Offline'}`"
    >
      <CharacterAvatar
        class="party-rail__avatar"
        :name="name"
        :portrait-url="portraitUrl"
        size="rail"
      />
    </OverlayBadge>
    <CharacterAvatar
      v-else
      class="party-rail__avatar"
      :name="name"
      :portrait-url="portraitUrl"
      size="rail"
    />

    <div
      v-if="expanded"
      class="party-rail__character-details"
    >
      <span class="party-rail__entry-name d-block text-truncate">
        {{ name }}
      </span>
      <span
        v-if="showPresence"
        class="visually-hidden"
      >
        — {{ connected ? "Connected" : "Offline" }}
      </span>
      <span
        v-if="currentHp !== null && maxHp !== null"
        class="d-block small text-body-secondary tabular-nums"
      >
        {{ currentHp }} / {{ maxHp }} HP
      </span>
      <span
        v-if="current"
        class="d-block small fw-semibold"
      >
        <span
          class="mdi mdi-sword-cross me-1"
          aria-hidden="true"
        />
        Current turn
      </span>
      <ProgressBar
        v-if="healthPercentage !== null"
        :value="healthPercentage"
        :show-value="false"
        :aria-label="healthLabel"
      />
      <slot />
    </div>
    <ProgressBar
      v-else-if="healthPercentage !== null"
      class="party-rail__compact-health"
      :value="healthPercentage"
      :show-value="false"
      :aria-label="healthLabel"
    />
  </li>
</template>

<script lang="ts">
import OverlayBadge from "primevue/overlaybadge";
import ProgressBar from "primevue/progressbar";
import { defineComponent, type PropType } from "vue";
import CharacterAvatar from "./CharacterAvatar.vue";

export default defineComponent({
  components: {
    CharacterAvatar,
    OverlayBadge,
    ProgressBar,
  },
  props: {
    name: { type: String, required: true },
    portraitUrl: {
      type: String as PropType<string | null>,
      default: null,
    },
    connected: { type: Boolean, default: false },
    showPresence: { type: Boolean, default: false },
    expanded: { type: Boolean, default: false },
    currentHp: { type: Number as PropType<number | null>, default: null },
    maxHp: { type: Number as PropType<number | null>, default: null },
    healthPercentage: {
      type: Number as PropType<number | null>,
      default: null,
    },
    current: { type: Boolean, default: false },
  },
  computed: {
    healthLabel(): string {
      if (this.currentHp !== null && this.maxHp !== null) {
        return `${this.name} health: ${this.currentHp} of ${this.maxHp}`;
      }

      return `${this.name} health bar`;
    },
    healthState(): "critical" | "wounded" | "healthy" | "unknown" {
      if (this.healthPercentage === null) {
        return "unknown";
      }

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
