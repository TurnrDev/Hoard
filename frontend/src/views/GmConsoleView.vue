<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ItemPickerDialog from "../components/ItemPickerDialog.vue";
import {
  getCampaign,
  getItems,
  createInventoryTransaction,
  createMoneyTransfer,
  createSharedXpAward,
  type Campaign,
  type Item,
} from "../api";
import type { PickerCandidate } from "../itemPicker";

const route = useRoute();
const router = useRouter();
const campaignId = Number(route.params.id);
const campaign = ref<Campaign>();
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const xpAmount = ref(10);
const xpPreview = ref<number>();
const previewError = ref("");
const characterId = ref<number>();
const itemId = ref<number>();
const takeItemId = ref<number>();
const quantity = ref(1);
const description = ref("");
const coinDenomination = ref("gp");
const coinAmount = ref(1);
let previewTimer: ReturnType<typeof setTimeout> | undefined;

const characters = computed(
  () =>
    campaign.value?.characters.map((character) => ({
      title: character.name,
      value: character.id,
    })) ?? [],
);
const catalogueCandidates = computed<PickerCandidate[]>(() =>
  items.value.map((item) => ({ item })),
);
const selectedCharacter = computed(() =>
  campaign.value?.characters.find(
    (character) => character.id === characterId.value,
  ),
);
const inventoryCandidates = computed<PickerCandidate[]>(
  () =>
    selectedCharacter.value?.inventory.flatMap((entry) => {
      const item = items.value.find(
        (candidate) => candidate.id === entry.item_id,
      );
      return item ? [{ item, quantity: entry.quantity }] : [];
    }) ?? [],
);

async function load(): Promise<void> {
  try {
    const [nextCampaign, nextItems] = await Promise.all([
      getCampaign(campaignId),
      getItems(campaignId),
    ]);
    if (!nextCampaign.is_game_master) {
      await router.replace(`/c/${campaignId}`);
      return;
    }
    campaign.value = nextCampaign;
    items.value = nextItems;
    characterId.value ??= nextCampaign.characters[0]?.id;
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load GM controls.";
  }
}

async function previewXp(): Promise<void> {
  previewError.value = "";
  if (!Number.isInteger(xpAmount.value) || xpAmount.value <= 0) {
    xpPreview.value = undefined;
    return;
  }
  const recipients =
    campaign.value?.characters.filter(
      (character) => character.is_active && character.is_player_character,
    ).length ?? 0;
  xpPreview.value = recipients
    ? Math.floor(xpAmount.value / recipients)
    : undefined;
  if (!recipients)
    previewError.value = "No active player characters can receive XP.";
}

watch(xpAmount, () => {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(previewXp, 250);
});
watch(inventoryCandidates, (candidates) => {
  if (!candidates.some((candidate) => candidate.item.id === takeItemId.value))
    takeItemId.value = undefined;
});

async function postIntent(
  request: Promise<unknown>,
  success: string,
): Promise<void> {
  try {
    await request;
    notice.value = success;
    description.value = "";
    await load();
    await previewXp();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Action failed.";
  }
}

onMounted(async () => {
  await load();
  await previewXp();
});
</script>

<template>
  <v-container fluid class="pa-md-8" style="max-width: 1300px">
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <div class="text-overline text-secondary">Game master controls</div>
        <h1 class="text-h3">{{ campaign?.name }}</h1>
      </div>
      <v-btn :to="`/c/${campaignId}`" prepend-icon="mdi-arrow-left"
        >Campaign</v-btn
      >
    </div>
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
    <v-row>
      <v-col cols="12" md="6"
        ><v-card class="pa-4 h-100" color="surface"
          ><v-card-title class="text-h5"
            ><v-icon color="primary" class="mr-2">mdi-star-four-points</v-icon
            >Give shared XP</v-card-title
          ><v-card-text
            ><v-text-field
              v-model.number="xpAmount"
              type="number"
              min="1"
              label="Total encounter XP"
            /><v-sheet rounded class="pa-4 mb-3" color="background"
              ><div class="text-caption">Live preview</div>
              <div v-if="xpPreview" class="text-h3 text-primary">
                {{ xpPreview }} XP each
              </div>
              <div v-else class="text-medium-emphasis">
                Enter a valid XP amount.
              </div>
              <div v-if="previewError" class="text-error text-caption">
                {{ previewError }}
              </div></v-sheet
            ><v-textarea
              v-model="description"
              label="Reason / encounter"
            /><v-btn
              block
              color="primary"
              size="large"
              @click="
                postIntent(
                  createSharedXpAward(campaignId, {
                    amount: xpAmount,
                    description,
                  }),
                  'Shared XP awarded.',
                )
              "
              >Award XP</v-btn
            ></v-card-text
          ></v-card
        ></v-col
      >
      <v-col cols="12" md="6"
        ><v-card class="pa-4 h-100" color="surface"
          ><v-card-title class="text-h5"
            ><v-icon color="primary" class="mr-2">mdi-gift</v-icon>Give
            item</v-card-title
          ><v-card-text
            ><v-select
              v-model="characterId"
              :items="characters"
              label="Character"
            /><ItemPickerDialog
              v-model="itemId"
              :candidates="catalogueCandidates"
              label="Item to grant"
            /><v-text-field
              v-model.number="quantity"
              type="number"
              min="1"
              label="Quantity"
            /><v-textarea v-model="description" label="Reason" /><v-btn
              block
              color="primary"
              size="large"
              :disabled="!characterId || !itemId"
              @click="
                postIntent(
                  createInventoryTransaction(campaignId, {
                    from_character_id: null,
                    to_character_id: characterId ?? null,
                    item_id: itemId ?? 0,
                    quantity,
                    description,
                  }),
                  'Item granted.',
                )
              "
              >Give item</v-btn
            ></v-card-text
          ></v-card
        ></v-col
      >
      <v-col cols="12" md="6"
        ><v-card class="pa-4 h-100" color="surface"
          ><v-card-title class="text-h5"
            ><v-icon color="error" class="mr-2"
              >mdi-package-variant-remove</v-icon
            >Take item</v-card-title
          ><v-card-text
            ><v-select
              v-model="characterId"
              :items="characters"
              label="Character"
            /><ItemPickerDialog
              v-model="takeItemId"
              :candidates="inventoryCandidates"
              label="Item in inventory"
              no-data-text="This character has no recorded items."
            /><v-text-field
              v-model.number="quantity"
              type="number"
              min="1"
              label="Quantity"
            /><v-textarea v-model="description" label="Reason" /><v-btn
              block
              color="error"
              size="large"
              :disabled="!characterId || !takeItemId"
              @click="
                postIntent(
                  createInventoryTransaction(campaignId, {
                    from_character_id: characterId ?? null,
                    to_character_id: null,
                    item_id: takeItemId ?? 0,
                    quantity,
                    description,
                  }),
                  'Item returned to the system account.',
                )
              "
              >Take item</v-btn
            ></v-card-text
          ></v-card
        ></v-col
      >
      <v-col cols="12" md="6"
        ><v-card class="pa-4 h-100" color="surface"
          ><v-card-title class="text-h5"
            ><v-icon color="primary" class="mr-2">mdi-coins</v-icon>Give or take
            coins</v-card-title
          ><v-card-text
            ><v-select
              v-model="characterId"
              :items="characters"
              label="Character"
            /><v-select
              v-model="coinDenomination"
              :items="['cp', 'sp', 'ep', 'gp', 'pp']"
              label="Denomination"
            /><v-text-field
              v-model.number="coinAmount"
              type="number"
              min="1"
              label="Amount"
            /><v-textarea v-model="description" label="Reason" />
            <div class="d-flex ga-3">
              <v-btn
                class="flex-grow-1"
                color="primary"
                size="large"
                :disabled="!characterId"
                @click="
                  postIntent(
                    createMoneyTransfer(campaignId, {
                      from_character_id: null,
                      to_character_id: characterId ?? null,
                      amounts: { [coinDenomination]: coinAmount },
                      description,
                    }),
                    'Coins granted.',
                  )
                "
                >Give coins</v-btn
              ><v-btn
                class="flex-grow-1"
                color="error"
                size="large"
                :disabled="!characterId"
                @click="
                  postIntent(
                    createMoneyTransfer(campaignId, {
                      from_character_id: characterId ?? null,
                      to_character_id: null,
                      amounts: { [coinDenomination]: coinAmount },
                      description,
                    }),
                    'Coins taken.',
                  )
                "
                >Take coins</v-btn
              >
            </div></v-card-text
          ></v-card
        ></v-col
      >
    </v-row>
  </v-container>
</template>
