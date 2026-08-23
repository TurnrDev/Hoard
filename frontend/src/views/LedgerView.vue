<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  getCampaign,
  getTransactions,
  reverseTransaction,
  type Campaign,
  type LedgerTransaction,
} from "../api";
import { useCampaignRefresh } from "../realtime";
import { displayCoin, displayIdentifier } from "../display";

const campaignId = Number(useRoute().params.id);
const campaign = ref<Campaign>();
const transactions = ref<LedgerTransaction[]>([]);
const error = ref("");
const reversing = ref<LedgerTransaction>();

function names(transaction: LedgerTransaction, positive: boolean): string {
  return [
    ...new Set(
      transaction.entries
        .filter((entry) => (positive ? entry.amount > 0 : entry.amount < 0))
        .map((entry) => entry.account_name),
    ),
  ].join(", ");
}

function amount(transaction: LedgerTransaction): string {
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
}

function typeIcon(transaction: LedgerTransaction): string {
  return (
    {
      experience: "mdi-star-four-points",
      money: "mdi-cash-multiple",
      inventory: "mdi-package-variant",
      health: "mdi-heart-pulse",
      character: "mdi-account-edit-outline",
    }[transaction.ledger] ?? "mdi-book-open-variant"
  );
}

function canReverse(transaction: LedgerTransaction): boolean {
  return Boolean(
    campaign.value?.is_game_master &&
    ["inventory", "money", "experience"].includes(transaction.ledger) &&
    !transaction.is_reversed &&
    !transaction.reversal_of_id,
  );
}

async function load(): Promise<void> {
  try {
    const [next, history] = await Promise.all([
      getCampaign(campaignId),
      getTransactions(campaignId),
    ]);
    campaign.value = next;
    transactions.value = history.results;
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load ledger.";
  }
}

async function reverse(): Promise<void> {
  if (!reversing.value) return;
  try {
    await reverseTransaction(campaignId, reversing.value);
    reversing.value = undefined;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to reverse transaction.";
  }
}

onMounted(load);
useCampaignRefresh(load);
</script>

<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Immutable audit history</div>
        <h1>Ledger</h1>
      </div>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-card>
      <v-table class="a11y-table ledger-table">
        <caption class="visually-hidden">Immutable campaign audit history</caption>
        <thead>
          <tr>
            <th scope="col">Real datetime</th>
            <th scope="col">Campaign date</th>
            <th scope="col">Type</th>
            <th scope="col">From</th>
            <th scope="col">To</th>
            <th scope="col">Amount</th>
            <th scope="col">Description</th>
            <th scope="col">By</th>
            <th scope="col"><span class="visually-hidden">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="transaction in transactions"
            :key="`${transaction.ledger}-${transaction.id}`"
          >
            <th scope="row">
              {{ new Date(transaction.occurred_at).toLocaleString() }}
            </th>
            <td>{{ transaction.campaign_date ?? "Campaign date unavailable" }}</td>
            <td>
              <v-icon
                :icon="typeIcon(transaction)"
                size="small"
                color="primary"
              />
              {{ transaction.ledger_label ?? displayIdentifier(transaction.ledger) }}
            </td>
            <td>{{ names(transaction, false) }}</td>
            <td>{{ names(transaction, true) }}</td>
            <td>{{ amount(transaction) }}</td>
            <td>
              {{ transaction.description || "—" }}
              <span
                v-if="transaction.is_reversed"
                class="text-error"
              >
                (reversed)
              </span>
            </td>
            <td>{{ transaction.actor || "—" }}</td>
            <td>
              <v-btn
                v-if="canReverse(transaction)"
                icon="mdi-undo"
                size="small"
                variant="text"
                :aria-label="`Reverse ${transaction.ledger_label ?? displayIdentifier(transaction.ledger)} transaction`"
                @click="reversing = transaction"
              />
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
    <v-dialog
      :model-value="Boolean(reversing)"
      max-width="480"
      @update:model-value="
        (open) => {
          if (!open) reversing = undefined;
        }
      "
    >
      <v-card title="Reverse transaction">
        <v-card-text>
          This creates the final compensating entry. The original remains in history.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="reversing = undefined">Cancel</v-btn>
          <v-btn
            color="error"
            @click="reverse"
          >
            Reverse
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
