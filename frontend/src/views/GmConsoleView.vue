<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatGoldValue } from "../money";
import { formatCoinPouch } from "../display";
import GmCoinForm from "../components/GmCoinForm.vue";
import GmCalendarCard from "../components/GmCalendarCard.vue";
import GmItemForm from "../components/GmItemForm.vue";
import GmSharedXpForm from "../components/GmSharedXpForm.vue";
import {
  approveCampaignLevel,
  getCampaign,
  getCharacters,
  getItems,
  type Campaign,
  type Character,
  type Item,
} from "../api";
import { useCampaignRefresh } from "../realtime";
import { createSnackbarDismissHandler } from "../dismissibleMessage";
const route = useRoute();
const router = useRouter();
const contextId = Number(route.params.id);
const campaign = ref<Campaign>();
const characters = ref<Character[]>([]);
const items = ref<Item[]>([]);
const error = ref("");
const notice = ref("");
const clearErrorWhenClosed = createSnackbarDismissHandler(error);
const clearNoticeWhenClosed = createSnackbarDismissHandler(notice);
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

function updateCalendar(calendar: Campaign["calendar"]): void {
  if (!campaign.value) {
    return;
  }

  campaign.value = { ...campaign.value, calendar };
}

async function approveLevel(): Promise<void> {
  try {
    await approveCampaignLevel(contextId);
    notice.value = "Campaign level approved.";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to level up.";
  }
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
      @update:model-value="clearErrorWhenClosed"
    >
      {{ error }}
    </v-snackbar>
    <v-snackbar
      :model-value="Boolean(notice)"
      color="success"
      @update:model-value="clearNoticeWhenClosed"
    >
      {{ notice }}
    </v-snackbar>
    <v-alert
      v-if="campaign?.incomplete_level_ups.length"
      type="error"
      variant="tonal"
      class="mb-4"
      title="Group level-up is incomplete"
    >
      Waiting for
      {{ campaign.incomplete_level_ups.map((row) => row.character_name).join(", ") }}
      to finish level {{ campaign.level }}.
    </v-alert>
    <v-alert
      v-else-if="campaign && campaign.eligible_level > campaign.level"
      type="warning"
      variant="tonal"
      class="mb-4"
      title="The group has earned a level"
    >
      The campaign has enough XP for level {{ campaign.level + 1 }}.
      <template #append>
        <v-btn
          color="primary"
          @click="approveLevel"
        >
          Approve group level-up
        </v-btn>
      </template>
    </v-alert>
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
          @changed="updateCalendar"
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
                  {{ formatCoinPouch(campaign.party_money) }}
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
    <div
      v-if="campaign"
      class="text-overline text-secondary mb-2"
    >
      GM actions
    </div>
    <v-row
      v-if="campaign"
      class="gm-actions"
    >
      <v-col
        cols="12"
        md="4"
      >
        <GmSharedXpForm
          :context-id="contextId"
          :characters="characters"
          :level="campaign.level"
          :shared-experience="campaign.shared_experience"
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
    <v-progress-linear
      v-else-if="!error"
      indeterminate
      aria-label="Loading GM controls"
    />
  </v-container>
</template>
