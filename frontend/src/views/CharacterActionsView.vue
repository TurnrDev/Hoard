<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import {
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  getCampaign,
  getItems,
  getMyCharacters,
  type Campaign,
  type Character,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";

const campaignId = Number(useRoute().params.id);
const campaign = ref<Campaign>();
const ownCharacters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const tab = ref("items");
const sourceId = ref<number>();
const destinationId = ref<number | null>(null);
const itemId = ref<number>();
const quantity = ref(1);
const transferDenomination = ref("gp");
const transferAmount = ref(1);
const exchangeCharacterId = ref<number>();
const givenDenomination = ref("gp");
const givenAmount = ref(1);
const receivedDenomination = ref("sp");
const receivedAmount = ref(10);
const description = ref("");

const ownOptions = computed(() => ownCharacters.value.filter((character) => character.is_active && !character.is_archived).map((character) => ({ title: character.name, value: character.id })));
const destinationOptions = computed(() => [
  { title: "Campaign store", value: null },
  ...(campaign.value?.characters.filter((character) => character.is_active && !character.is_archived).map((character) => ({ title: character.name, value: character.id })) ?? []),
]);
const sourceCharacter = computed(() => ownCharacters.value.find((character) => character.id === sourceId.value));
const inventoryCandidates = computed<PickerCandidate[]>(() => sourceCharacter.value?.inventory.flatMap((entry) => {
  const item = items.value.find((candidate) => candidate.id === entry.item_id);
  return item ? [{ item, quantity: entry.quantity }] : [];
}) ?? []);
const denominations = ["cp", "sp", "ep", "gp", "pp"];

async function load(): Promise<void> {
  try {
    const [nextCampaign, nextCharacters, nextItems] = await Promise.all([getCampaign(campaignId), getMyCharacters(campaignId), getItems(campaignId)]);
    campaign.value = nextCampaign;
    ownCharacters.value = nextCharacters;
    items.value = nextItems;
    sourceId.value ??= ownOptions.value[0]?.value;
    exchangeCharacterId.value ??= ownOptions.value[0]?.value;
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "Unable to load character actions.";
  }
}

watch(inventoryCandidates, (candidates) => {
  if (!candidates.some((candidate) => candidate.item.id === itemId.value)) itemId.value = undefined;
});

async function moveItem(): Promise<void> {
  if (!sourceId.value || !itemId.value || destinationId.value === undefined) return;
  try {
    await createInventoryTransaction(campaignId, { from_character_id: sourceId.value, to_character_id: destinationId.value, item_id: itemId.value, quantity: quantity.value, description: description.value });
    notice.value = "Item moved.";
    description.value = "";
    await load();
  } catch (exception) { error.value = exception instanceof Error ? exception.message : "Unable to move item."; }
}

async function transferMoney(): Promise<void> {
  if (!sourceId.value || destinationId.value === undefined) return;
  try {
    await createMoneyTransfer(campaignId, { from_character_id: sourceId.value, to_character_id: destinationId.value, amounts: { [transferDenomination.value]: transferAmount.value }, description: description.value });
    notice.value = "Money transferred.";
    description.value = "";
    await load();
  } catch (exception) { error.value = exception instanceof Error ? exception.message : "Unable to transfer money."; }
}

async function exchangeMoney(): Promise<void> {
  if (!exchangeCharacterId.value) return;
  try {
    await createMoneyExchange(campaignId, { character_id: exchangeCharacterId.value, given: { [givenDenomination.value]: givenAmount.value }, received: { [receivedDenomination.value]: receivedAmount.value }, description: description.value });
    notice.value = "Money exchanged.";
    description.value = "";
    await load();
  } catch (exception) { error.value = exception instanceof Error ? exception.message : "Unable to exchange money."; }
}

onMounted(load);
</script>

<template>
  <v-container style="max-width: 960px">
    <div class="d-flex align-center justify-space-between mb-6">
      <div><div class="text-overline text-secondary">Character actions</div><h1 class="text-h4">Move belongings and money</h1></div>
      <v-btn :to="`/c/${campaignId}`" prepend-icon="mdi-arrow-left">Campaign</v-btn>
    </div>
    <v-alert v-if="error" type="error" closable class="mb-4" @click:close="error = ''">{{ error }}</v-alert>
    <v-alert v-if="notice" type="success" closable class="mb-4" @click:close="notice = ''">{{ notice }}</v-alert>
    <v-alert type="info" variant="tonal" class="mb-4">You can move items from your character, send your character’s money to another character or the campaign store, and exchange your own coins.</v-alert>
    <v-tabs v-model="tab"><v-tab value="items">Move item</v-tab><v-tab value="transfer">Send money</v-tab><v-tab value="exchange">Exchange money</v-tab></v-tabs>
    <v-window v-model="tab" class="pt-4">
      <v-window-item value="items"><v-card><v-card-text>
        <v-select v-model="sourceId" :items="ownOptions" label="Your character" />
        <ItemPickerDialog v-model="itemId" :candidates="inventoryCandidates" label="Item to move" no-data-text="This character has no recorded items." />
        <v-select v-model="destinationId" :items="destinationOptions" label="Move to" />
        <v-text-field v-model.number="quantity" type="number" min="1" label="Quantity" />
        <v-textarea v-model="description" label="Note (optional)" />
        <v-btn color="primary" :disabled="!sourceId || !itemId || destinationId === undefined" @click="moveItem">Move item</v-btn>
      </v-card-text></v-card></v-window-item>
      <v-window-item value="transfer"><v-card><v-card-text>
        <v-select v-model="sourceId" :items="ownOptions" label="Your character" />
        <v-select v-model="destinationId" :items="destinationOptions" label="Send to" />
        <v-row><v-col><v-select v-model="transferDenomination" :items="denominations" label="Denomination" /></v-col><v-col><v-text-field v-model.number="transferAmount" type="number" min="1" label="Amount" /></v-col></v-row>
        <v-textarea v-model="description" label="Note (optional)" />
        <v-btn color="primary" :disabled="!sourceId || destinationId === undefined" @click="transferMoney">Send money</v-btn>
      </v-card-text></v-card></v-window-item>
      <v-window-item value="exchange"><v-card><v-card-text>
        <v-select v-model="exchangeCharacterId" :items="ownOptions" label="Your character" />
        <v-row><v-col><v-select v-model="givenDenomination" :items="denominations" label="Give denomination" /><v-text-field v-model.number="givenAmount" type="number" min="1" label="Give amount" /></v-col><v-col><v-select v-model="receivedDenomination" :items="denominations" label="Receive denomination" /><v-text-field v-model.number="receivedAmount" type="number" min="1" label="Receive amount" /></v-col></v-row>
        <v-textarea v-model="description" label="Note (optional)" />
        <v-btn color="primary" :disabled="!exchangeCharacterId" @click="exchangeMoney">Exchange money</v-btn>
      </v-card-text></v-card></v-window-item>
    </v-window>
  </v-container>
</template>
