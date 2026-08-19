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
  return transaction.entries
    .filter((entry) => entry.amount > 0)
    .map(
      (entry) =>
        `${entry.amount} ${entry.item_name ?? entry.denomination ?? "XP"}`,
    )
    .join(" · ");
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
      exception instanceof Error
        ? exception.message
        : "Unable to reverse transaction.";
  }
}
onMounted(load);
</script>

<template>
  <v-container class="page-shell"
    ><header class="page-heading">
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
      >{{ error }}</v-alert
    ><v-card
      ><v-table class="ledger-table"
        ><thead>
          <tr>
            <th>When</th>
            <th>From</th>
            <th>To</th>
            <th>Amount</th>
            <th>Description</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="transaction in transactions"
            :key="`${transaction.ledger}-${transaction.id}`"
          >
            <td>{{ new Date(transaction.created_at).toLocaleString() }}</td>
            <td>{{ names(transaction, false) }}</td>
            <td>{{ names(transaction, true) }}</td>
            <td>{{ amount(transaction) }}</td>
            <td>
              {{ transaction.description || "—" }}
              <span v-if="transaction.is_reversed" class="text-error"
                >(reversed)</span
              >
            </td>
            <td>
              <v-btn
                v-if="
                  campaign?.is_game_master &&
                  !transaction.is_reversed &&
                  !transaction.reversal_of_id
                "
                icon="mdi-undo"
                size="small"
                variant="text"
                @click="reversing = transaction"
              />
            </td>
          </tr></tbody></v-table></v-card
    ><v-dialog
      :model-value="Boolean(reversing)"
      max-width="480"
      @update:model-value="
        (open) => {
          if (!open) reversing = undefined;
        }
      "
      ><v-card title="Reverse transaction"
        ><v-card-text
          >This creates the final compensating entry. The original remains in
          history.</v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="reversing = undefined">Cancel</v-btn
          ><v-btn color="error" @click="reverse">Reverse</v-btn></v-card-actions
        ></v-card
      ></v-dialog
    ></v-container
  >
</template>
