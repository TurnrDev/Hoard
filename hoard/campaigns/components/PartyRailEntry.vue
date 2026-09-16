<template>
  <li class="party-rail__entry party-rail__entry--unknown align-items-center">
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
    </div>
  </li>
</template>

<script lang="ts">
import OverlayBadge from "primevue/overlaybadge";
import { defineComponent, type PropType } from "vue";
import CharacterAvatar from "./CharacterAvatar.vue";

export default defineComponent({
  components: {
    CharacterAvatar,
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
  },
});
</script>
