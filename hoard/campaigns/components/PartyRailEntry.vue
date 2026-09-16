<template>
  <li
    class="party-rail__entry align-items-center"
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
      <HealthBar
        v-if="healthPercentage !== null"
        :percentage="healthPercentage"
        :label="healthLabel"
      />
      <slot />
    </div>
    <HealthBar
      v-else-if="healthPercentage !== null"
      class="party-rail__compact-health"
      :percentage="healthPercentage"
      :label="healthLabel"
    />
  </li>
</template>

<script lang="ts">
import OverlayBadge from "primevue/overlaybadge";
import { defineComponent, type PropType } from "vue";
import CharacterAvatar from "./CharacterAvatar.vue";
import HealthBar from "./HealthBar.vue";

export default defineComponent({
  components: {
    CharacterAvatar,
    HealthBar,
    OverlayBadge,
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
  },
});
</script>
