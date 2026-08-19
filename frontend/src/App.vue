<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getCampaigns, logout, type CampaignSummary } from "./api";

const router = useRouter();
const busy = ref(false);
const campaigns = ref<CampaignSummary[]>([]);

onMounted(async () => {
  try {
    campaigns.value = await getCampaigns();
  } catch {
    campaigns.value = [];
  }
});

async function signOut(): Promise<void> {
  busy.value = true;
  await logout();
  await router.push("/login");
  busy.value = false;
}
</script>

<template>
  <v-app>
    <v-app-bar color="surface" density="comfortable">
      <v-app-bar-title class="font-weight-black text-primary"
        >HOARD</v-app-bar-title
      >
      <v-menu v-if="$route.path !== '/login' && campaigns.length > 1">
        <template #activator="{ props }">
          <v-btn v-bind="props" icon="mdi-account-circle" variant="text" />
        </template>
        <v-list density="compact">
          <v-list-subheader>Switch campaign</v-list-subheader>
          <v-list-item
            v-for="campaign in campaigns"
            :key="campaign.id"
            :title="campaign.name"
            :subtitle="campaign.is_game_master ? 'Game master' : 'Player'"
            @click="router.push(`/c/${campaign.id}`)"
          />
          <v-list-item title="All campaigns" @click="router.push('/')" />
        </v-list>
      </v-menu>
      <v-btn
        v-if="$route.path !== '/login'"
        :loading="busy"
        icon="mdi-logout"
        variant="text"
        @click="signOut"
      />
    </v-app-bar>
    <v-main><router-view /></v-main>
  </v-app>
</template>
