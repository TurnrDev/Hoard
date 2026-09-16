<template>
  <section aria-labelledby="gm-desk-title">
    <header class="mb-5">
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Game Master desk
        </p>
        <h1
          id="gm-desk-title"
          class="display-5 mb-2"
        >
          {{ campaign?.name ?? "Campaign controls" }}
        </h1>
        <p class="mb-0 text-body-secondary">
          {{ activePcCount }} active player{{ activePcCount === 1 ? "" : "s" }}
        </p>
      </div>
    </header>

    <Message
      v-if="error"
      severity="error"
      closable
      @close="error = ''"
    >
      {{ error }}
    </Message>

    <template v-if="campaign">
      <div class="row g-4 mb-5">
        <div class="col-12 col-lg-6">
          <GmCalendarCard
            :context-id="contextId"
            :calendar="campaign.calendar"
          />
        </div>
        <div class="col-12 col-lg-6">
          <section
            class="border rounded-3 p-3 p-md-4 h-100"
            aria-labelledby="party-resources-heading"
          >
            <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
              Shared resources
            </p>
            <h2
              id="party-resources-heading"
              class="h4"
            >
              Party coin
            </h2>
            <p class="fs-5 mb-4 tabular-nums">
              {{ formatCoinPouch(campaign.party_money) }}
            </p>
            <div class="border-top pt-3">
              <p class="small text-body-secondary mb-1">Party wealth</p>
              <p class="h3 mb-0 tabular-nums">
                {{ formatGoldValue(campaign.party_money.gold_value) }} GP
              </p>
            </div>
          </section>
        </div>
      </div>

      <section aria-labelledby="gm-actions-heading">
        <header class="mb-3">
          <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
            Campaign commands
          </p>
          <h2
            id="gm-actions-heading"
            class="h3 mb-0"
          >
            Award and distribute
          </h2>
        </header>
        <div class="row g-4">
          <section class="col-12 col-xl-6">
            <GmSharedXpForm
              :context-id="contextId"
              :characters="characters"
              :level="campaign.level"
              :shared-experience="campaign.shared_experience"
              @completed="completed"
            />
          </section>
          <section class="col-12 col-xl-6">
            <GmCoinForm
              :context-id="contextId"
              :characters="characters"
              @completed="completed"
            />
          </section>
        </div>
      </section>
    </template>

    <ProgressBar
      v-else-if="!error"
      indeterminate
      aria-label="Loading GM controls"
    />
  </section>
</template>

<script lang="ts">
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import { defineComponent } from "vue";
import { formatCoinPouch } from "@/campaigns/display";
import { formatGoldValue } from "@/campaigns/money";
import GmCalendarCard from "@/campaigns/components/GmCalendarCard.vue";
import GmCoinForm from "@/campaigns/components/GmCoinForm.vue";
import GmSharedXpForm from "@/campaigns/components/GmSharedXpForm.vue";
import { getCampaign, type Campaign, type Character } from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: {
    GmCalendarCard,
    GmCoinForm,
    GmSharedXpForm,
    Message,
    ProgressBar,
  },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      characters: [] as Character[],
      error: "",
    };
  },
  computed: {
    contextId(): number {
      return Number(this.$route.params.id);
    },
    activePcCount(): number {
      return this.characters.filter(
        (character) => character.is_active && character.is_player_character,
      ).length;
    },
    campaignRefresh(): number {
      return campaignRefreshRevision.value;
    },
  },
  watch: {
    campaignRefresh(): void {
      void this.load();
    },
  },
  mounted() {
    void this.load();
  },
  methods: {
    formatCoinPouch,
    formatGoldValue,
    async load(): Promise<void> {
      try {
        const campaign = await getCampaign(this.contextId);

        if (!campaign.is_game_master) {
          await this.$router.replace(`/c/${this.contextId}`);
          return;
        }

        this.campaign = campaign;
        this.characters = campaign.characters;
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load GM controls.";
      }
    },
    async completed(message: string): Promise<void> {
      this.$toast.add({
        severity: "success",
        summary: message,
        life: 4_000,
      });
      await this.load();
    },
  },
});
</script>
