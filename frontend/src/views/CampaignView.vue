<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  createItem,
  getCampaign,
  getItems,
  getTransactions,
  reverseTransaction,
  type Campaign,
  type EquipmentMetadata,
  type Item,
  type LedgerTransaction,
} from "../api";
import { itemSummary } from "../itemPicker";

const route = useRoute();
const campaignId = Number(route.params.id);
const campaign = ref<Campaign>();
const items = ref<Item[]>([]);
const transactions = ref<LedgerTransaction[]>([]);
const error = ref("");
const notice = ref("");
const tab = ref("characters");
const catalogueSearch = ref("");
const description = ref("");
const itemDialog = ref(false);
const itemName = ref("");
const itemDescription = ref("");
const itemMetadata = ref<Partial<EquipmentMetadata>>({});
const reverseDialog = ref(false);
const transactionToReverse = ref<LedgerTransaction>();

const isGM = computed(() => campaign.value?.is_game_master ?? false);
const filteredCatalogue = computed(() => {
  const query = catalogueSearch.value.trim().toLocaleLowerCase();
  if (!query) return items.value;
  return items.value.filter((item) =>
    [
      item.name,
      item.description,
      item.source_system,
      item.equipment.source_book,
      item.equipment.category,
      item.equipment.item_type,
    ]
      .filter((value): value is string => Boolean(value))
      .join(" ")
      .toLocaleLowerCase()
      .includes(query),
  );
});

function uniqueAccountNames(
  transaction: LedgerTransaction,
  direction: "from" | "to",
): string {
  const isFrom = direction === "from";
  return [
    ...new Set(
      transaction.entries
        .filter((entry) => (isFrom ? entry.amount < 0 : entry.amount > 0))
        .map((entry) => entry.account_name),
    ),
  ].join(", ");
}

function transactionAmount(transaction: LedgerTransaction): string {
  const positiveEntries = transaction.entries.filter(
    (entry) => entry.amount > 0,
  );
  return positiveEntries
    .map(
      (entry) =>
        `${entry.amount} ${entry.item_name ?? entry.denomination ?? "XP"}`,
    )
    .join(" · ");
}

async function refresh(): Promise<void> {
  error.value = "";
  try {
    const [nextCampaign, nextItems, history] = await Promise.all([
      getCampaign(campaignId),
      getItems(campaignId),
      getTransactions(campaignId),
    ]);
    campaign.value = nextCampaign;
    localStorage.setItem("hoard:last-campaign", String(campaignId));
    items.value = nextItems;
    transactions.value = history.results;
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load campaign.";
  }
}

onMounted(refresh);

async function submitItem(): Promise<void> {
  try {
    await createItem(
      campaignId,
      itemName.value,
      itemDescription.value,
      itemMetadata.value,
    );
    itemDialog.value = false;
    itemName.value = "";
    itemDescription.value = "";
    itemMetadata.value = {};
    await refresh();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Could not create item.";
  }
}

async function reverse(): Promise<void> {
  if (!transactionToReverse.value) return;
  try {
    await reverseTransaction(campaignId, transactionToReverse.value);
    reverseDialog.value = false;
    await refresh();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Could not reverse transaction.";
  }
}
</script>

<template>
  <v-container fluid class="pa-md-8">
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
      >{{ error }}</v-alert
    ><v-alert
      v-if="notice"
      type="success"
      closable
      class="mb-4"
      @click:close="notice = ''"
      >{{ notice }}</v-alert
    >
    <template v-if="campaign">
      <div
        class="d-flex flex-wrap align-center justify-space-between mb-6 ga-4"
      >
        <div>
          <div class="text-overline text-secondary">Campaign</div>
          <h1 class="text-h3">{{ campaign.name }}</h1>
        </div>
        <div class="d-flex ga-2">
          <v-btn
            v-if="isGM"
            color="primary"
            prepend-icon="mdi-controller"
            :to="`/c/${campaignId}/gm`"
            >GM controls</v-btn
          ><v-btn
            prepend-icon="mdi-account"
            :to="`/c/${campaignId}/characters/me`"
            >My characters</v-btn
          ><v-btn
            prepend-icon="mdi-swap-horizontal"
            :to="`/c/${campaignId}/actions`"
            >Character actions</v-btn
          ><v-btn
            v-if="isGM"
            prepend-icon="mdi-cog"
            :to="`/c/${campaignId}/manage`"
            >Manage</v-btn
          ><v-btn
            prepend-icon="mdi-package-variant-plus"
            @click="itemDialog = true"
            >New item</v-btn
          >
        </div>
      </div>
      <v-row class="mb-2"
        ><v-col cols="12" md="3"
          ><v-card
            ><v-card-text
              ><div class="text-overline">Shared XP</div>
              <div class="text-h3">{{ campaign.shared_experience }}</div>
              <div class="text-caption">
                per active player character
              </div></v-card-text
            ></v-card
          ></v-col
        ><v-col cols="12" md="3"
          ><v-card
            ><v-card-text
              ><div class="text-overline">Characters</div>
              <div class="text-h3">
                {{ campaign.characters.length }}
              </div></v-card-text
            ></v-card
          ></v-col
        ><v-col cols="12" md="3"
          ><v-card
            ><v-card-text
              ><div class="text-overline">Role</div>
              <div class="text-h5">
                {{ isGM ? "Game master" : "Player" }}
              </div></v-card-text
            ></v-card
          ></v-col
        ><v-col cols="12" md="3"
          ><v-card
            ><v-card-text
              ><div class="text-overline">Party money</div>
              <div class="text-h5">{{ campaign.party_money.gold_value }} ¤</div>
              <div class="text-caption">
                {{ campaign.party_money.pp }} pp ·
                {{ campaign.party_money.gp }} gp ·
                {{ campaign.party_money.ep }} ep ·
                {{ campaign.party_money.sp }} sp ·
                {{ campaign.party_money.cp }} cp
              </div></v-card-text
            ></v-card
          ></v-col
        ></v-row
      >
      <v-tabs v-model="tab" color="primary"
        ><v-tab value="characters">Characters</v-tab
        ><v-tab value="items">Equipment</v-tab
        ><v-tab value="history">Ledger</v-tab></v-tabs
      >
      <v-window v-model="tab" class="pt-4">
        <v-window-item value="characters"
          ><v-row
            ><v-col
              v-for="character in campaign.characters"
              :key="character.id"
              cols="12"
              md="6"
              ><v-card
                ><v-card-title
                  >{{ character.name }}
                  <v-chip size="small" class="ml-2"
                    >{{ character.race }} {{ character.class }}</v-chip
                  ></v-card-title
                ><v-card-text
                  ><v-row dense
                    ><v-col cols="4"
                      ><strong>{{ character.experience }}</strong
                      ><br /><span class="text-caption">XP</span></v-col
                    ><v-col cols="8"
                      ><strong>{{ character.money.pp }} pp</strong> ·
                      {{ character.money.gp }} gp · {{ character.money.ep }} ep
                      · {{ character.money.sp }} sp ·
                      {{ character.money.cp }} cp<br /><span
                        class="text-caption"
                        >{{ character.money.gold_value }} gp total</span
                      ></v-col
                    ></v-row
                  ><v-divider class="my-3" />
                  <div v-if="character.inventory.length">
                    <v-chip
                      v-for="entry in character.inventory"
                      :key="entry.item_id"
                      class="mr-2 mb-2"
                      >{{ entry.quantity }} × {{ entry.name }}</v-chip
                    >
                  </div>
                  <span v-else class="text-medium-emphasis"
                    >No inventory recorded.</span
                  ></v-card-text
                ></v-card
              ></v-col
            ></v-row
          ></v-window-item
        >
        <v-window-item value="items"
          ><v-text-field
            v-model="catalogueSearch"
            prepend-inner-icon="mdi-magnify"
            label="Search equipment"
            clearable
          />
          <div class="text-caption mb-3">
            {{ filteredCatalogue.length }} matching items
          </div>
          <v-virtual-scroll
            :items="filteredCatalogue"
            :item-height="210"
            height="700"
            ><template #default="{ item }"
              ><v-card :key="item.id" class="ma-2"
                ><v-card-title>{{ item.name }}</v-card-title
                ><v-card-subtitle>{{
                  itemSummary(item) || "Campaign custom item"
                }}</v-card-subtitle
                ><v-card-text
                  ><p class="catalogue-description">
                    {{ item.description || "No description." }}
                  </p>
                  <v-chip
                    v-if="item.equipment.category"
                    size="small"
                    class="mr-1 mb-1"
                    >{{ item.equipment.category }}</v-chip
                  ><v-chip
                    v-if="item.equipment.item_type"
                    size="small"
                    class="mr-1 mb-1"
                    >{{ item.equipment.item_type }}</v-chip
                  ><v-chip
                    v-if="item.equipment.rarity"
                    size="small"
                    class="mr-1 mb-1"
                    >{{ item.equipment.rarity }}</v-chip
                  ><v-chip
                    v-if="item.equipment.is_magic"
                    size="small"
                    class="mr-1 mb-1"
                    >magic</v-chip
                  ><v-chip
                    v-if="item.equipment.requires_attunement"
                    size="small"
                    class="mr-1 mb-1"
                    >attunement</v-chip
                  >
                  <div
                    v-if="item.created_by_username"
                    class="text-caption mt-2"
                  >
                    Created by {{ item.created_by_username }}
                  </div></v-card-text
                ></v-card
              ></template
            ></v-virtual-scroll
          ></v-window-item
        >
        <v-window-item value="history"
          ><v-table
            ><thead>
              <tr>
                <th>When</th>
                <th>Ledger</th>
                <th>From</th>
                <th>To</th>
                <th>Amount</th>
                <th>Description</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="transaction in transactions"
                :key="`${transaction.ledger}-${transaction.id}`"
              >
                <td>{{ new Date(transaction.created_at).toLocaleString() }}</td>
                <td>
                  <v-chip size="small">{{ transaction.ledger }}</v-chip>
                </td>
                <td class="ledger-amount-negative">
                  {{ uniqueAccountNames(transaction, "from") }}
                </td>
                <td class="ledger-amount-positive">
                  {{ uniqueAccountNames(transaction, "to") }}
                </td>
                <td>{{ transactionAmount(transaction) }}</td>
                <td>
                  {{ transaction.description || "—" }}
                  <span v-if="transaction.is_reversed" class="text-error"
                    >(reversed)</span
                  >
                </td>
                <td>
                  <v-btn
                    v-if="
                      isGM &&
                      !transaction.is_reversed &&
                      !transaction.reversal_of_id
                    "
                    icon="mdi-undo"
                    size="small"
                    @click="
                      transactionToReverse = transaction;
                      description = '';
                      reverseDialog = true;
                    "
                  />
                </td>
              </tr></tbody></v-table
        ></v-window-item>
      </v-window> </template
    ><v-progress-circular v-else indeterminate color="primary" />

    <v-dialog v-model="itemDialog" max-width="700"
      ><v-card title="Create campaign item"
        ><v-card-text
          ><v-text-field v-model="itemName" label="Name" /><v-textarea
            v-model="itemDescription"
            label="Description" /><v-row dense
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.category"
                label="Category" /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.item_type"
                label="Type" /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.source_book"
                label="Source book" /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.rarity"
                label="Rarity" /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.cost_amount"
                label="Cost amount"
                type="number" /></v-col
            ><v-col cols="6"
              ><v-select
                v-model="itemMetadata.cost_currency"
                :items="['cp', 'sp', 'ep', 'gp', 'pp']"
                label="Cost currency"
                clearable /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.weight_amount"
                label="Weight"
                type="number" /></v-col
            ><v-col cols="6"
              ><v-text-field
                v-model="itemMetadata.weight_unit"
                label="Weight unit"
                placeholder="pounds" /></v-col
            ><v-col cols="6"
              ><v-select
                v-model="itemMetadata.is_magic"
                :items="[
                  { title: 'Unknown', value: null },
                  { title: 'Magic', value: true },
                  { title: 'Non-magic', value: false },
                ]"
                label="Magic" /></v-col
            ><v-col cols="6"
              ><v-select
                v-model="itemMetadata.requires_attunement"
                :items="[
                  { title: 'Unknown', value: null },
                  { title: 'Required', value: true },
                  { title: 'Not required', value: false },
                ]"
                label="Attunement" /></v-col></v-row></v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="itemDialog = false">Cancel</v-btn
          ><v-btn color="primary" @click="submitItem"
            >Create</v-btn
          ></v-card-actions
        ></v-card
      ></v-dialog
    >
    <v-dialog v-model="reverseDialog" max-width="520"
      ><v-card title="Reverse transaction"
        ><v-card-actions
          ><v-spacer /><v-btn @click="reverseDialog = false">Cancel</v-btn
          ><v-btn color="error" @click="reverse">Reverse</v-btn></v-card-actions
        ></v-card
      ></v-dialog
    >
  </v-container>
</template>

<style scoped>
.catalogue-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
