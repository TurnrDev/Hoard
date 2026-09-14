<template>
  <section
    class="party-summary"
    :class="{ 'party-summary--expanded border rounded-3 p-3': expanded }"
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
        class="party-summary__desktop d-none d-lg-flex border-top pt-2 pb-1"
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
        class="party-summary__mobile d-lg-none border-top mb-0 pt-2 text-center small tabular-nums"
      >
        <strong>Party</strong>
        · {{ campaign.shared_experience.toLocaleString() }} XP ·
        {{ formatGoldValue(campaign.party_money.gold_value ?? 0) }} ¤
      </p>
    </template>
  </section>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import type { Campaign } from "../api";
import { formatCoinPouch } from "../display";
import { formatCompactMoneyValue, formatGoldValue } from "../money";

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
    formatCoinPouch,
    formatGoldValue,
  },
});
</script>

<style scoped>
.party-summary {
  position: sticky;
  z-index: 1;
  bottom: 0;
  margin-top: auto;
  background: var(--bs-tertiary-bg);
}

.party-summary__desktop {
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.65rem;
  line-height: 1.2;
  text-align: center;
}

.party-summary__desktop .mdi {
  color: var(--bs-secondary-color);
  font-size: 1rem;
}

.party-summary__mobile {
  overflow-x: auto;
  white-space: nowrap;
}

@media (max-width: 991.98px) {
  .party-summary {
    width: 100%;
  }

  .party-summary--expanded {
    padding: 0.75rem !important;
  }

  .party-summary--expanded h3,
  .party-summary--expanded dl > div {
    margin-bottom: 0.75rem !important;
  }

  .party-summary--expanded dl > div:last-child {
    margin-bottom: 0 !important;
  }

  .party-summary--expanded dd.fs-5 {
    font-size: 1rem !important;
  }
}
</style>
