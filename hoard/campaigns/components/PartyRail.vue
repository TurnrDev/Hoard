<template>
  <aside
    class="party-rail d-flex flex-column h-100"
    :class="{ 'party-rail--expanded': expanded }"
    aria-label="Party Rail"
  >
    <div
      class="party-rail__content d-flex"
      :class="expanded ? 'flex-column' : 'flex-row flex-lg-column'"
    >
      <header class="party-rail__header d-flex align-items-center">
        <h2 class="visually-hidden">Party Rail</h2>
        <Button
          class="d-none d-lg-inline-flex"
          :icon="expanded ? 'mdi mdi-menu-open' : 'mdi mdi-menu'"
          text
          rounded
          :aria-label="expanded ? 'Collapse Party Rail' : 'Expand Party Rail'"
          :aria-expanded="expanded"
          @click="$emit('toggle')"
        />
        <Button
          class="party-rail__mobile-toggle d-lg-none"
          :icon="expanded ? 'mdi mdi-chevron-up' : 'mdi mdi-account-group-outline'"
          text
          rounded
          :aria-label="expanded ? 'Collapse Party Rail' : 'Expand Party Rail'"
          :aria-expanded="expanded"
          @click="$emit('toggle')"
        />
        <span
          v-if="expanded"
          class="ms-1 fw-bold"
        >
          {{ inCombat ? "Initiative" : "Party" }}
        </span>
      </header>

      <section class="party-rail__group">
        <ul
          class="party-rail__entries d-flex list-unstyled mb-0"
          :class="expanded ? 'flex-column' : 'flex-row flex-lg-column'"
        >
          <GameMasterPresence
            v-for="member in gameMasters"
            :key="member.id"
            :member="member"
            :expanded="expanded"
          />
        </ul>
      </section>

      <div
        class="party-rail__separator d-flex align-items-center gap-2 fw-bold text-uppercase"
        role="separator"
      >
        <span
          class="party-rail__separator-line"
          aria-hidden="true"
        />
        <span v-if="expanded && inCombat">Combatants</span>
        <span
          v-if="expanded && inCombat"
          class="party-rail__separator-line"
          aria-hidden="true"
        />
      </div>

      <InitiativeTracker
        v-if="inCombat"
        :combatants="campaign.encounter?.combatants ?? []"
        :active-context="activeContext"
        :expanded="expanded"
        :can-view-hidden-health="activeContext.kind === 'gm'"
        :current-combatant-id="campaign.encounter?.current_combatant_id ?? null"
      />
      <PartyRoster
        v-else
        :characters="campaign.characters"
        :members="members"
        :active-context="activeContext"
        :expanded="expanded"
      />
    </div>

    <PartySummary
      :campaign="campaign"
      :expanded="expanded"
    />
  </aside>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import Button from "primevue/button";
import type { Campaign, CampaignMember } from "@/api";
import type { ActingContext } from "@/campaigns/context";
import GameMasterPresence from "./GameMasterPresence.vue";
import InitiativeTracker from "./InitiativeTracker.vue";
import PartyRoster from "./PartyRoster.vue";
import PartySummary from "./PartySummary.vue";

export default defineComponent({
  components: {
    GameMasterPresence,
    InitiativeTracker,
    PartyRoster,
    PartySummary,
    Button,
  },
  props: {
    campaign: { type: Object as PropType<Campaign>, required: true },
    members: { type: Array as PropType<CampaignMember[]>, required: true },
    activeContext: { type: Object as PropType<ActingContext>, required: true },
    expanded: { type: Boolean, default: false },
  },
  emits: ["toggle"],
  computed: {
    inCombat(): boolean {
      return this.campaign.encounter !== null;
    },
    gameMasters(): CampaignMember[] {
      return this.members.filter((member) => member.is_game_master && member.is_active);
    },
  },
});
</script>
