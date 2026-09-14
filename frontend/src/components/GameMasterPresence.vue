<template>
  <li class="party-rail__entry party-rail__entry--game-master align-items-center">
    <OverlayBadge
      :value="member.connected ? '✓' : '○'"
      :severity="member.connected ? 'success' : 'secondary'"
      :aria-label="`${displayName} — ${member.connected ? 'Connected' : 'Offline'}`"
    >
      <Avatar
        class="party-rail__avatar"
        :label="initials"
        shape="circle"
      />
    </OverlayBadge>
    <div
      v-if="expanded"
      class="party-rail__character-details"
    >
      <span class="party-rail__entry-name d-block text-truncate">
        {{ displayName }}
        <span class="visually-hidden">
          — {{ member.connected ? "Connected" : "Offline" }}
        </span>
      </span>
      <span class="d-block text-truncate small text-body-secondary">Game Master</span>
    </div>
    <span
      v-else
      class="party-rail__compact-role d-flex align-items-center justify-content-center border rounded-pill bg-body-secondary text-body-secondary text-center fw-bold"
    >
      GM
    </span>
  </li>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Avatar from "primevue/avatar";
import OverlayBadge from "primevue/overlaybadge";
import type { CampaignMember } from "../api";

export default defineComponent({
  components: { Avatar, OverlayBadge },
  props: {
    member: { type: Object as PropType<CampaignMember>, required: true },
    expanded: { type: Boolean, default: false },
  },
  computed: {
    displayName(): string {
      return this.member.first_name.trim() || this.member.username;
    },
    initials(): string {
      if (this.member.first_name.trim()) {
        return [this.member.first_name, this.member.last_name]
          .filter((name) => name.trim())
          .map((name) => name.trim()[0])
          .join("")
          .toUpperCase();
      }

      return this.member.username
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase();
    },
  },
});
</script>
