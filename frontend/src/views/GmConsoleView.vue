<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatGoldValue } from "../money";
import GmCoinForm from "../components/GmCoinForm.vue";
import GmCalendarCard from "../components/GmCalendarCard.vue";
import GmItemForm from "../components/GmItemForm.vue";
import GmSharedXpForm from "../components/GmSharedXpForm.vue";
import {
  getCampaign,
  getCharacters,
  getItems,
  type Campaign,
  type Character,
  type Item,
} from "../api";
import { useCampaignRefresh } from "../realtime";
const route = useRoute();
const router = useRouter();
const contextId = Number(route.params.id);
const campaign = ref<Campaign>();
const characters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const activePcCount = computed(
  () =>
    characters.value.filter(
      (character) => character.is_active && character.is_player_character,
    ).length,
);

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
useCampaignRefresh(load);
</script>
<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Campaign dashboard</div>
        <h1>{{ campaign?.name }}</h1>
        <v-chip
          size="small"
          variant="tonal"
          prepend-icon="mdi-account-group-outline"
        >
          {{ activePcCount }} active players
        </v-chip>
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
      dense
      class="profile-overview mb-4"
    >
      <v-col
        cols="12"
        md="5"
      >
        <GmCalendarCard
          :context-id="contextId"
          :calendar="campaign.calendar"
          @changed="(calendar) => (campaign = { ...campaign!, calendar })"
        />
      </v-col>
      <v-col
        cols="12"
        md="7"
      >
        <v-card class="profile-card h-100 coin-summary-card">
          <v-row
            no-gutters
            class="h-100"
          >
            <v-col
              cols="12"
              sm="7"
            >
              <v-card-text>
                <div class="text-overline">Party coin</div>
                <div class="money-line mt-3">
                  {{ campaign.party_money.pp }} pp · {{ campaign.party_money.gp }} gp ·
                  {{ campaign.party_money.ep }} ep · {{ campaign.party_money.sp }} sp ·
                  {{ campaign.party_money.cp }} cp
                </div>
              </v-card-text>
            </v-col>
            <v-col
              cols="12"
              sm="5"
              class="coin-value-pane"
            >
              <v-card-text>
                <div class="text-overline">Party wealth</div>
                <div class="text-h4 mt-3">
                  {{ formatGoldValue(campaign.party_money.gold_value) }} ¤
                </div>
              </v-card-text>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
    <div class="text-overline text-secondary mb-2">GM actions</div>
    <v-row class="gm-actions">
      <v-col
        cols="12"
        md="4"
      >
        <GmSharedXpForm
          :context-id="contextId"
          :characters="characters"
          @completed="completed"
        />
      </v-col>
      <v-col
        cols="12"
        md="4"
      >
        <GmItemForm
          :context-id="contextId"
          :items="items"
          @completed="completed"
        />
      </v-col>
      <v-col
        cols="12"
        md="4"
      >
        <GmCoinForm
          :context-id="contextId"
          @completed="completed"
        />
      </v-col>
    </v-row>
  </v-container>
</template>
