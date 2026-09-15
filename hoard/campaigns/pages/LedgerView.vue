<template>
  <section aria-labelledby="ledger-title">
    <header class="mb-5">
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Immutable audit history
        </p>
        <h1
          id="ledger-title"
          class="display-5 mb-0"
        >
          Ledger
        </h1>
      </div>
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
      class="table-responsive border rounded-3"
      aria-labelledby="ledger-title"
    >
      <table class="table table-striped table-hover align-middle mb-0">
        <caption>Immutable campaign audit history</caption>
        <thead>
          <tr>
            <th scope="col">When</th>
            <th scope="col">Campaign date</th>
            <th scope="col">Type</th>
            <th scope="col">From</th>
            <th scope="col">To</th>
            <th scope="col">Amount</th>
            <th scope="col">Description</th>
            <th scope="col">By</th>
            <th
              scope="col"
              class="text-end"
            >
              <span class="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="transaction in transactions"
            :key="`${transaction.ledger}-${transaction.id}`"
          >
            <th scope="row">
              <RelativeTime :value="transaction.occurred_at" />
            </th>
            <td>{{ transaction.campaign_date ?? "Campaign date unavailable" }}</td>
            <td>
              <span
                :class="['mdi', typeIcon(transaction)]"
                aria-hidden="true"
              />
              {{
                transaction.ledger_label ??
                displayTransactionIdentifier(transaction.ledger)
              }}
            </td>
            <td>{{ names(transaction, false) }}</td>
            <td>{{ names(transaction, true) }}</td>
            <td class="tabular-nums">{{ amount(transaction) }}</td>
            <td>
              {{ transaction.description || "—" }}
              <span
                v-if="transaction.is_reversed"
                class="badge text-bg-secondary ms-1"
              >
                (reversed)
              </span>
            </td>
            <td>{{ transaction.actor || "—" }}</td>
            <td class="text-end">
              <Button
                v-if="canReverse(transaction)"
                icon="mdi mdi-undo"
                size="small"
                text
                :aria-label="`Reverse ${transaction.ledger_label ?? displayTransactionIdentifier(transaction.ledger)} transaction`"
                @click="reversing = transaction"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </section>
    <Dialog
      :visible="Boolean(reversing)"
      modal
      :style="{ width: 'min(30rem, calc(100vw - 2rem))' }"
      @update:visible="
        (open: boolean) => {
          if (!open) {
            reversing = undefined;
          }
        }
      "
    >
      <section
        class="d-grid gap-3"
        aria-labelledby="reverse-transaction-heading"
      >
        <h2
          id="reverse-transaction-heading"
          class="h3"
        >
          Reverse transaction
        </h2>
        <p class="mb-0">
          This creates the final compensating entry. The original remains in history.
        </p>
        <footer class="d-flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            outlined
            @click="reversing = undefined"
          />
          <Button
            severity="danger"
            label="Reverse"
            @click="reverse"
          />
        </footer>
      </section>
    </Dialog>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import { defineComponent } from "vue";
import {
  getCampaign,
  getTransactions,
  reverseTransaction,
  type Campaign,
  type LedgerTransaction,
} from "@/api";
import { campaignRefreshRevision } from "@/realtime";
import { displayCoin, displayIdentifier } from "@/campaigns/display";
import RelativeTime from "@/components/RelativeTime.vue";

export default defineComponent({
  components: { Button, Dialog, Message, RelativeTime },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      transactions: [] as LedgerTransaction[],
      error: "",
      reversing: undefined as LedgerTransaction | undefined,
    };
  },
  computed: {
    campaignId(): number {
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
    displayTransactionIdentifier(value: string): string {
      return displayIdentifier(value);
    },
    names(transaction: LedgerTransaction, positive: boolean): string {
      return [
        ...new Set(
          transaction.entries
            .filter((entry) => (positive ? entry.amount > 0 : entry.amount < 0))
            .map((entry) => entry.account_name),
        ),
      ].join(", ");
    },

    amount(transaction: LedgerTransaction): string {
      if (transaction.ledger === "health") {
        return [
          transaction.current_hp_delta
            ? `${transaction.current_hp_delta > 0 ? "+" : ""}${transaction.current_hp_delta} HP`
            : "",
          transaction.temporary_hp_delta
            ? `${transaction.temporary_hp_delta > 0 ? "+" : ""}${transaction.temporary_hp_delta} temp HP`
            : "",
        ]
          .filter(Boolean)
          .join(" · ");
      }
      if (transaction.ledger === "character") {
        return `${Object.keys(transaction.changes ?? {}).length} field changes`;
      }
      if (transaction.ledger === "condition") {
        return transaction.condition
          ? displayIdentifier(transaction.condition)
          : "Condition";
      }
      if (transaction.ledger.startsWith("audit.")) {
        return `${Object.keys(transaction.changes ?? {}).length} recorded changes`;
      }
      return transaction.entries
        .filter((entry) => entry.amount > 0)
        .map(
          (entry) =>
            `${entry.amount} ${entry.item_name ?? (entry.denomination ? displayCoin(entry.denomination) : "XP")}`,
        )
        .join(" · ");
    },

    typeIcon(transaction: LedgerTransaction): string {
      return (
        {
          experience: "mdi-star-four-points",
          money: "mdi-cash-multiple",
          inventory: "mdi-package-variant",
          health: "mdi-heart-pulse",
          character: "mdi-account-edit-outline",
          condition: "mdi-account-alert-outline",
        }[transaction.ledger] ?? "mdi-book-open-variant"
      );
    },

    canReverse(transaction: LedgerTransaction): boolean {
      return Boolean(
        this.campaign?.is_game_master &&
        ["inventory", "money", "experience"].includes(transaction.ledger) &&
        !transaction.is_reversed &&
        !transaction.reversal_of_id,
      );
    },

    async load(): Promise<void> {
      try {
        const [next, history] = await Promise.all([
          getCampaign(this.campaignId),
          getTransactions(this.campaignId),
        ]);
        this.campaign = next;
        this.transactions = history.results;
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load ledger.";
      }
    },

    async reverse(): Promise<void> {
      if (!this.reversing) {
        return;
      }
      try {
        await reverseTransaction(this.campaignId, this.reversing);
        this.reversing = undefined;
        await this.load();
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to reverse transaction.";
      }
    },
  },
});
</script>
