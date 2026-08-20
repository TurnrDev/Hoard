<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatGoldValue } from "../money";
import GmCoinForm from "../components/GmCoinForm.vue";
import GmGiveItemForm from "../components/GmGiveItemForm.vue";
import GmSharedXpForm from "../components/GmSharedXpForm.vue";
import GmTakeItemForm from "../components/GmTakeItemForm.vue";
import {
  getCampaign,
  getCharacters,
  getItems,
  type Campaign,
  type Character,
  type Item,
} from "../api";
const route = useRoute();
const router = useRouter();
const contextId = Number(route.params.id);
const campaign = ref<Campaign>();
const characters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");

async function load(): Promise<void> {
  try {
    const [nextCampaign, nextCharacters, nextItems] = await Promise.all([
      getCampaign(contextId),
      getCharacters(contextId),
      getItems(contextId),
    ]);
    if (!nextCampaign.is_game_master) {
      await router.replace(`/c/${contextId}`);
      return;
    }
    campaign.value = nextCampaign;
    characters.value = nextCharacters;
    items.value = nextItems;
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load GM controls.";
  }
}

async function completed(message: string): Promise<void> {
  notice.value = message;
  await load();
}

onMounted(load);
</script>
<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Campaign dashboard</div>
        <h1>{{ campaign?.name }}</h1>
      </div>
      <v-btn
        :to="`/c/${contextId}/characters`"
        prepend-icon="mdi-account-group-outline"
      >
        Roster
      </v-btn>
    </header>
    <v-snackbar
      :model-value="Boolean(error)"
      color="error"
      @update:model-value="(visible) => !visible && (error = '')"
    >
      {{ error }}
    </v-snackbar>
    <v-snackbar
      :model-value="Boolean(notice)"
      color="success"
      @update:model-value="(visible) => !visible && (notice = '')"
    >
      {{ notice }}
    </v-snackbar>
    <v-row
      v-if="campaign"
      class="mb-2"
    >
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text>
            <div class="text-overline">Party wealth</div>
            <div class="text-h5">
              {{ formatGoldValue(campaign.party_money.gold_value) }} ¤
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="6"
        md="3"
      >
        <v-card>
          <v-card-text>
            <div class="text-overline">Active PCs</div>
            <div class="text-h5">
              {{
                characters.filter(
                  (character) => character.is_active && character.is_player_character,
                ).length
              }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <v-card>
          <v-card-text>
            <div class="text-overline">Party coin</div>
            {{ campaign.party_money.pp }} pp · {{ campaign.party_money.gp }} gp ·
            {{ campaign.party_money.ep }} ep · {{ campaign.party_money.sp }} sp ·
            {{ campaign.party_money.cp }} cp
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <div class="text-overline text-secondary mb-2">GM actions</div>
    <v-row>
      <v-col
        cols="12"
        md="6"
      >
        <GmSharedXpForm
          :context-id="contextId"
          :characters="characters"
          @completed="completed"
        />
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <GmGiveItemForm
          :context-id="contextId"
          :items="items"
          @completed="completed"
        />
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <GmTakeItemForm
          :context-id="contextId"
          :items="items"
          @completed="completed"
        />
      </v-col>
      <v-col
        cols="12"
        md="6"
      >
        <GmCoinForm
          :context-id="contextId"
          @completed="completed"
        />
      </v-col>
    </v-row>
  </v-container>
</template>
