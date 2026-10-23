<template>
  <section aria-labelledby="ledger-title">
    <header class="mb-5">
      <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
        Party experience history
      </p>
      <h1
        id="ledger-title"
        class="display-5 mb-0"
      >
        Ledger
      </h1>
    </header>

    <Message
      v-if="error"
      severity="error"
      closable
      class="mb-4"
      @close="error = ''"
    >
      {{ error }}
    </Message>

    <section
      v-if="campaign"
      class="table-responsive border rounded-3"
    >
      <table class="table table-striped align-middle mb-0">
        <caption>Party experience award history</caption>
        <thead>
          <tr>
            <th scope="col">When</th>
            <th scope="col">Campaign date</th>
            <th scope="col">Description</th>
            <th
              scope="col"
              class="text-end"
            >
              Per player
            </th>
            <th
              scope="col"
              class="text-end"
            >
              Players
            </th>
            <th
              scope="col"
              class="text-end"
            >
              Remainder
            </th>
            <th scope="col">By</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="award in campaign.party_experience_awards"
            :key="award.id"
          >
            <th scope="row"><RelativeTime :value="award.occurred_at" /></th>
            <td>{{ award.campaign_date ?? "—" }}</td>
            <td>{{ description(award) }}</td>
            <td class="text-end tabular-nums">
              {{ formatXp(award.awarded_per_player) }}
            </td>
            <td class="text-end tabular-nums">{{ award.recipient_count }}</td>
            <td class="text-end tabular-nums">{{ award.discarded_amount }}</td>
            <td>{{ award.actor ?? "System" }}</td>
          </tr>
          <tr v-if="!campaign.party_experience_awards.length">
            <td
              colspan="7"
              class="text-center text-body-secondary py-4"
            >
              No party XP awards have been recorded yet.
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <ProgressBar
      v-else-if="!error"
      indeterminate
      aria-label="Loading ledger"
    />
  </section>
</template>

<script lang="ts">
import Message from "primevue/message";
import ProgressBar from "primevue/progressbar";
import { defineComponent } from "vue";
import { getCampaign, type Campaign, type PartyExperienceAward } from "@/api";
import RelativeTime from "@/components/RelativeTime.vue";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: { Message, ProgressBar, RelativeTime },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      error: "",
    };
  },
  computed: {
    contextId(): number {
      return Number(this.$route.params.id);
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
    formatXp(value: number): string {
      return `${value.toLocaleString()} XP`;
    },
    description(award: PartyExperienceAward): string {
      if (award.description) {
        return award.description;
      }

      return award.reason === "baseline" ? "Campaign XP baseline" : "Party XP award";
    },
    async load(): Promise<void> {
      try {
        this.campaign = await getCampaign(this.contextId);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load ledger.";
      }
    },
  },
});
</script>
