<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import {
  archiveCharacter,
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  getCampaign,
  getCharacters,
  getItems,
  getMyCharacters,
  updateCharacter,
  type Campaign,
  type Character,
  type Item,
} from "../api";
import { rememberContext } from "../context";
import type { PickerCandidate } from "../itemPicker";

const route = useRoute();
const router = useRouter();
const campaignId = Number(route.params.id);
const characterId = Number(route.params.characterId);
const campaign = ref<Campaign>();
const character = ref<Character>();
const ownCharacter = ref(false);
const characters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const action = ref("item");
const itemId = ref<number>();
const destinationId = ref<number | null>(null);
const quantity = ref(1);
const denomination = ref("gp");
const amount = ref(1);
const receivedDenomination = ref("sp");
const receivedAmount = ref(10);
const description = ref("");
const editOpen = ref(false);
const editName = ref("");
const editRace = ref("");
const editClass = ref("");
const editAbilities = ref({
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 10,
  charisma: 10,
});
const denominations = ["cp", "sp", "ep", "gp", "pp"];
const inventoryCandidates = computed<PickerCandidate[]>(
  () =>
    character.value?.inventory.flatMap((entry) => {
      const item = items.value.find(
        (candidate) => candidate.id === entry.item_id,
      );
      return item ? [{ item, quantity: entry.quantity }] : [];
    }) ?? [],
);
const destinationOptions = computed(() => [
  { title: "Campaign store", value: null },
  ...characters.value
    .filter((candidate) => candidate.is_active && !candidate.is_archived)
    .map((candidate) => ({ title: candidate.name, value: candidate.id })),
]);
const canAct = computed(
  () =>
    ownCharacter.value &&
    character.value?.is_active &&
    !character.value.is_archived,
);
const canEdit = computed(
  () => ownCharacter.value || campaign.value?.is_game_master,
);
const abilityScores = computed(() =>
  character.value
    ? [
        ["STR", character.value.strength],
        ["DEX", character.value.dexterity],
        ["CON", character.value.constitution],
        ["INT", character.value.intelligence],
        ["WIS", character.value.wisdom],
        ["CHA", character.value.charisma],
      ]
    : [],
);

async function load(): Promise<void> {
  try {
    const [nextCampaign, visible, own, nextItems] = await Promise.all([
      getCampaign(campaignId),
      getCharacters(campaignId),
      getMyCharacters(campaignId),
      getItems(campaignId),
    ]);
    campaign.value = nextCampaign;
    characters.value = visible;
    character.value =
      visible.find((candidate) => candidate.id === characterId) ??
      own.find((candidate) => candidate.id === characterId);
    ownCharacter.value = own.some((candidate) => candidate.id === characterId);
    items.value = nextItems;
    if (!character.value) await router.replace(`/c/${campaignId}/characters`);
    else if (
      ownCharacter.value &&
      character.value.is_active &&
      !character.value.is_archived
    )
      rememberContext({
        kind: "character",
        campaign: nextCampaign,
        character: character.value,
      });
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load character profile.";
  }
}

watch(inventoryCandidates, (candidates) => {
  if (!candidates.some((candidate) => candidate.item.id === itemId.value))
    itemId.value = undefined;
});

async function submit(): Promise<void> {
  if (!character.value) return;
  try {
    if (action.value === "item" && itemId.value)
      await createInventoryTransaction(campaignId, {
        from_character_id: character.value.id,
        to_character_id: destinationId.value,
        item_id: itemId.value,
        quantity: quantity.value,
        description: description.value,
      });
    if (action.value === "money")
      await createMoneyTransfer(campaignId, {
        from_character_id: character.value.id,
        to_character_id: destinationId.value,
        amounts: { [denomination.value]: amount.value },
        description: description.value,
      });
    if (action.value === "exchange")
      await createMoneyExchange(campaignId, {
        character_id: character.value.id,
        given: { [denomination.value]: amount.value },
        received: { [receivedDenomination.value]: receivedAmount.value },
        description: description.value,
      });
    notice.value = "Saved to the ledger.";
    description.value = "";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to complete this action.";
  }
}

function openEdit(): void {
  if (!character.value) return;
  editName.value = character.value.name;
  editRace.value = character.value.race;
  editClass.value = character.value.class;
  editAbilities.value = {
    strength: character.value.strength,
    dexterity: character.value.dexterity,
    constitution: character.value.constitution,
    intelligence: character.value.intelligence,
    wisdom: character.value.wisdom,
    charisma: character.value.charisma,
  };
  editOpen.value = true;
}

async function saveProfile(): Promise<void> {
  if (!character.value || !editName.value.trim()) return;
  try {
    await updateCharacter(campaignId, character.value.id, {
      name: editName.value.trim(),
      race: editRace.value,
      class: editClass.value,
      ...editAbilities.value,
    });
    editOpen.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to update character.";
  }
}

async function archive(): Promise<void> {
  if (!character.value) return;
  try {
    await archiveCharacter(campaignId, character.value.id);
    await router.replace(`/c/${campaignId}/characters`);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to archive character.";
  }
}

onMounted(load);
</script>

<template>
  <v-container class="page-shell" v-if="character">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Character profile</div>
        <h1>{{ character.name }}</h1>
        <p>{{ character.race }} · {{ character.class }}</p>
      </div>
      <div class="d-flex ga-2">
        <v-btn v-if="canEdit" @click="openEdit">Edit</v-btn>
        <v-btn
          :to="`/c/${campaignId}/characters`"
          prepend-icon="mdi-account-group-outline"
          >Roster</v-btn
        >
      </div>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = ''"
      >{{ error }}</v-alert
    >
    <v-alert
      v-if="notice"
      type="success"
      closable
      class="mb-4"
      @click:close="notice = ''"
      >{{ notice }}</v-alert
    >
    <v-row
      ><v-col cols="12" lg="7"
        ><v-card
          ><v-card-text
            ><v-row
              ><v-col cols="6"
                ><div class="text-overline">Experience</div>
                <div class="text-h4">{{ character.experience }}</div></v-col
              ><v-col cols="6"
                ><div class="text-overline">Total wealth</div>
                <div class="text-h4">
                  {{ character.money.gold_value }} ¤
                </div></v-col
              ></v-row
            ><v-divider class="my-4" />
            <div class="money-line">
              {{ character.money.pp }} pp · {{ character.money.gp }} gp ·
              {{ character.money.ep }} ep · {{ character.money.sp }} sp ·
              {{ character.money.cp }} cp
            </div>
            <v-divider class="my-4" /><v-row
              ><v-col
                v-for="[label, score] in abilityScores"
                :key="label"
                cols="4"
                sm="2"
                ><div class="ability">
                  <strong>{{ score }}</strong
                  ><span>{{ label }}</span>
                </div></v-col
              ></v-row
            ></v-card-text
          ></v-card
        >
        <v-card class="mt-4"
          ><v-card-title>Inventory</v-card-title
          ><v-card-text
            ><v-chip
              v-for="entry in character.inventory"
              :key="entry.item_id"
              class="mr-2 mb-2"
              >{{ entry.quantity }} × {{ entry.name }}</v-chip
            ><span
              v-if="!character.inventory.length"
              class="text-medium-emphasis"
              >No inventory recorded.</span
            ></v-card-text
          ></v-card
        ></v-col
      >
      <v-col cols="12" lg="5" v-if="canAct"
        ><v-card
          ><v-card-title>Actions</v-card-title
          ><v-card-text
            ><v-tabs v-model="action" grow
              ><v-tab value="item">Move</v-tab><v-tab value="money">Send</v-tab
              ><v-tab value="exchange">Exchange</v-tab></v-tabs
            ><v-window v-model="action" class="pt-4"
              ><v-window-item value="item"
                ><ItemPickerDialog
                  v-model="itemId"
                  :candidates="inventoryCandidates"
                  label="Item to move"
                  no-data-text="No recorded items." /><v-select
                  v-model="destinationId"
                  :items="destinationOptions"
                  label="Move to" /><v-text-field
                  v-model.number="quantity"
                  type="number"
                  min="1"
                  label="Quantity" /></v-window-item
              ><v-window-item value="money"
                ><v-select
                  v-model="destinationId"
                  :items="destinationOptions"
                  label="Send to" /><v-row
                  ><v-col
                    ><v-select
                      v-model="denomination"
                      :items="denominations"
                      label="Denomination" /></v-col
                  ><v-col
                    ><v-text-field
                      v-model.number="amount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col></v-row></v-window-item
              ><v-window-item value="exchange"
                ><v-row
                  ><v-col
                    ><v-select
                      v-model="denomination"
                      :items="denominations"
                      label="Give" /><v-text-field
                      v-model.number="amount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col
                  ><v-col
                    ><v-select
                      v-model="receivedDenomination"
                      :items="denominations"
                      label="Receive" /><v-text-field
                      v-model.number="receivedAmount"
                      type="number"
                      min="1"
                      label="Amount" /></v-col></v-row></v-window-item></v-window
            ><v-textarea
              v-model="description"
              label="Note (optional)"
              rows="2"
            /><v-btn
              block
              color="primary"
              :disabled="
                (action === 'item' && !itemId) ||
                (action !== 'exchange' && destinationId === undefined)
              "
              @click="submit"
              >{{
                action === "item"
                  ? "Move item"
                  : action === "money"
                    ? "Send money"
                    : "Exchange money"
              }}</v-btn
            ></v-card-text
          ></v-card
        ></v-col
      ></v-row
    >
    <v-dialog v-model="editOpen" max-width="720">
      <v-card title="Edit character">
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editName" label="Name"
            /></v-col>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editRace" label="Race"
            /></v-col>
            <v-col cols="12" sm="4"
              ><v-text-field v-model="editClass" label="Class"
            /></v-col>
          </v-row>
          <v-row>
            <v-col
              v-for="(_, ability) in editAbilities"
              :key="ability"
              cols="6"
              sm="4"
            >
              <v-text-field
                v-model.number="editAbilities[ability]"
                type="number"
                min="1"
                max="30"
                :label="ability[0].toUpperCase() + ability.slice(1)"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn color="error" variant="text" @click="archive">Archive</v-btn>
          <v-spacer />
          <v-btn @click="editOpen = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveProfile">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
