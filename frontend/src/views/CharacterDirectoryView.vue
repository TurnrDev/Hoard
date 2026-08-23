<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { formatGoldValue } from "../money";
import {
  getCampaign,
  getCharacters,
  getMyCharacters,
  type Campaign,
  type Character,
} from "../api";
import { useCampaignRefresh } from "../realtime";

const campaignId = Number(useRoute().params.id);
const campaign = ref<Campaign>();
const characters = ref<Character[]>([]);
const ownIds = ref(new Set<number>());
const error = ref("");
const playerCharacters = computed(() =>
  characters.value.filter((character) => character.is_player_character),
);
const hasNpcs = computed(() =>
  characters.value.some((character) => !character.is_player_character),
);

async function load(): Promise<void> {
  try {
    const [nextCampaign, visible, own] = await Promise.all([
      getCampaign(campaignId),
      getCharacters(campaignId),
      getMyCharacters(campaignId),
    ]);
    campaign.value = nextCampaign;
    characters.value = visible;
    ownIds.value = new Set(
      own
        .filter((character) => character.is_active && !character.is_archived)
        .map((character) => character.id),
    );
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to load characters.";
  }
}

function actingPath(character: Character): string {
  return character.context_id ? `/c/${character.context_id}` : "";
}

onMounted(load);
useCampaignRefresh(load);
</script>

<template>
  <v-container class="page-shell">
    <header class="page-heading">
      <div>
        <div class="text-overline text-secondary">Campaign roster</div>
        <h1>Characters</h1>
      </div>
      <v-btn
        :to="`/c/${campaignId}`"
        prepend-icon="mdi-home-variant-outline"
      >
        Home
      </v-btn>
    </header>
    <v-alert
      v-if="error"
      type="error"
      closable
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>
    <v-alert
      v-if="campaign?.is_game_master && campaign.incomplete_level_ups.length"
      type="error"
      variant="tonal"
      class="mb-4"
      title="Group level-up incomplete"
    >
      {{ campaign.incomplete_level_ups.map((row) => row.character_name).join(", ") }}
      still need to complete level {{ campaign.level }}.
    </v-alert>
    <v-row>
      <v-col
        v-for="character in playerCharacters"
        :key="character.id"
        cols="12"
        sm="6"
        lg="4"
      >
        <v-card class="h-100 character-card">
          <v-card-title>{{ character.name }}</v-card-title>
          <v-card-subtitle>
            {{ character.race }} · {{ character.class }}
          </v-card-subtitle>
          <v-card-text>
            <div class="text-h6">
              {{ formatGoldValue(character.money.gold_value) }} ¤
            </div>
            <div class="text-caption">
              {{ character.experience }} XP · {{ character.inventory.length }} inventory
              entries
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn :to="`/c/${campaignId}/characters/${character.id}`">
              View profile
            </v-btn>
            <v-btn
              v-if="ownIds.has(character.id)"
              color="primary"
              :to="actingPath(character)"
            >
              Open
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <section
      v-if="campaign?.is_game_master && hasNpcs"
      class="mt-8"
    >
      <div class="text-overline text-secondary mb-2">NPCs</div>
      <v-list class="rounded-lg">
        <v-list-item
          v-for="character in characters.filter(
            (candidate) => !candidate.is_player_character,
          )"
          :key="character.id"
          :title="character.name"
          :subtitle="`${character.race} · ${character.class}`"
          :to="`/c/${campaignId}/characters/${character.id}`"
          prepend-icon="mdi-account-star-outline"
        />
      </v-list>
    </section>
  </v-container>
</template>
