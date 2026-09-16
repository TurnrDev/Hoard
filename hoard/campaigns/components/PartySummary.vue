<template>
  <section
    class="party-summary sticky-bottom w-100 mt-auto bg-body-tertiary"
    :class="{ 'party-summary--expanded border rounded-3 p-2 p-lg-3': expanded }"
    aria-label="Party resources"
  >
    <template v-if="expanded">
      <h3 class="text-uppercase fw-semibold small text-body-secondary mb-3">
        Party resources
      </h3>
      <dl class="mb-0">
        <div class="mb-3">
          <dt class="small text-body-secondary">Party XP</dt>
          <dd class="fs-5 tabular-nums mb-0">
            {{ campaign.shared_experience.toLocaleString() }} XP
          </dd>
        </div>
        <div class="mb-3">
          <dt class="small text-body-secondary">Party money</dt>
          <dd class="small tabular-nums mb-0">
            {{ formatCoinPouch(campaign.party_money) }}
          </dd>
        </div>
        <div>
          <dt class="small text-body-secondary">Party wealth</dt>
          <dd class="fs-5 tabular-nums mb-0">
            {{ formatGoldValue(campaign.party_money.gold_value ?? 0) }} ¤
          </dd>
        </div>
      </dl>
    </template>
    <template v-else>
      <div
        class="party-summary__desktop d-none d-lg-flex flex-column align-items-center gap-1 border-top pt-2 pb-1 text-center"
        :title="collapsedSummary"
      >
        <span
          class="mdi mdi-star-four-points-outline"
          aria-hidden="true"
        />
        <strong class="tabular-nums">{{ compactExperience }} XP</strong>
        <span
          class="mdi mdi-cash-multiple"
          aria-hidden="true"
        />
        <strong class="tabular-nums">{{ compactWealth }} ¤</strong>
      </div>
      <p
        class="party-summary__mobile d-lg-none d-flex align-items-center justify-content-center gap-1 overflow-auto text-nowrap border-top mb-0 pt-2 small tabular-nums"
      >
        <span>{{ formatCampaignDate(campaign.calendar) }}</span>
        <span aria-hidden="true">·</span>
        <strong>Party</strong>
        <span aria-hidden="true">·</span>
        <span>{{ campaign.shared_experience.toLocaleString() }} XP</span>
        <span aria-hidden="true">·</span>
        <span>{{ formatGoldValue(campaign.party_money.gold_value ?? 0) }} ¤</span>
      </p>
    </template>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { Campaign } from "@/api";
import { formatCampaignDate } from "@/campaigns/calendar";
import { formatCoinPouch } from "@/campaigns/display";
import { formatCompactMoneyValue, formatGoldValue } from "@/campaigns/money";

export default defineComponent({
  props: {
    campaign: { type: Object as PropType<Campaign>, required: true },
    expanded: { type: Boolean, default: false },
  },
  computed: {
    collapsedSummary(): string {
      return `${this.campaign.shared_experience.toLocaleString()} party XP; ${this.formatGoldValue(this.campaign.party_money.gold_value ?? 0)} party wealth`;
    },
    compactExperience(): string {
      return Intl.NumberFormat(undefined, {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(this.campaign.shared_experience);
    },
    compactWealth(): string {
      return formatCompactMoneyValue(this.campaign.party_money.gold_value ?? 0);
    },
  },
  methods: {
    formatCampaignDate,
    formatCoinPouch,
    formatGoldValue,
  },
});
</script>

<style scoped>
.party-summary__desktop {
  font-size: 0.65rem;
  line-height: 1.2;
}

.party-summary__desktop .mdi {
  color: var(--bs-secondary-color);
  font-size: 1rem;
}

@media (max-width: 991.98px) {
  .party-summary--expanded dd.fs-5 {
    font-size: 1rem !important;
  }
}
</style>
