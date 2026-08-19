<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getCampaigns, type CampaignSummary } from "../api";

const campaigns = ref<CampaignSummary[]>([]);
const error = ref("");
onMounted(async () => {
  try {
    campaigns.value = await getCampaigns();
  } catch (exception) {
    error.value = String(exception);
  }
});
</script>

<template>
  <v-container>
    <h1 class="text-h4 mb-6">Your campaigns</h1>
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-row>
      <v-col v-for="campaign in campaigns" :key="campaign.id" cols="12" md="6">
        <v-card :to="`/campaigns/${campaign.id}`" hover>
          <v-card-title>{{ campaign.name }}</v-card-title>
          <v-card-subtitle>{{
            campaign.is_game_master ? "Game master" : "Player"
          }}</v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>
    <v-alert v-if="!error && !campaigns.length" type="info"
      >You are not yet a member of a campaign.</v-alert
    >
  </v-container>
</template>
