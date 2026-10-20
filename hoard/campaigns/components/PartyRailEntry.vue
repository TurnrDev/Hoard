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
        v-if="hasDetailedHealth"
        class="d-block small text-body-secondary tabular-nums"
      >
        {{ currentHp }} / {{ maxHp }} HP
        <template v-if="temporaryHp > 0">· +{{ temporaryHp }} temporary</template>
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
        v-if="hasHealthIndicator"
        :current="currentHp"
        :maximum="maxHp"
        :percentage="healthPercentage"
        :label="`${name} health status`"
        :temporary="temporaryHp"
        compact
      />
      <slot />
    </div>
    <HealthBar
      v-else-if="hasHealthIndicator"
      class="party-rail__compact-health"
      :current="currentHp"
      :maximum="maxHp"
      :percentage="healthPercentage"
      :label="`${name} health status`"
      :temporary="temporaryHp"
      compact
    />
    <span
      v-if="!expanded && temporaryHp > 0"
      class="party-rail__temporary-hp small tabular-nums"
      :aria-label="`${temporaryHp} temporary hit points`"
    >
      <span
        class="mdi mdi-shield-plus-outline"
        aria-hidden="true"
      />
      +{{ temporaryHp }}
    </span>
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
    healthPercentage: { type: Number as PropType<number | null>, default: null },
    temporaryHp: { type: Number, default: 0 },
    current: { type: Boolean, default: false },
  },
  computed: {
    hasDetailedHealth(): boolean {
      return this.currentHp !== null && this.maxHp !== null;
    },
    hasHealthIndicator(): boolean {
      return this.hasDetailedHealth || this.healthPercentage !== null;
    },
  },
});
</script>

<style scoped>
.party-rail__temporary-hp {
  grid-column: 1 / -1;
  color: var(--hoard-health-temporary);
}
</style>
