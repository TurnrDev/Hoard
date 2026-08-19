<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getContexts, type CampaignContext } from "../api";

const contexts = ref<CampaignContext[]>([]);
const error = ref("");
const router = useRouter();
onMounted(async () => {
  try {
    contexts.value = await getContexts();
    const saved = Number(localStorage.getItem("hoard:last-context"));
    const target =
      contexts.value.find((context) => context.id === saved) ??
      (contexts.value.length === 1 ? contexts.value[0] : undefined);
    if (target) await router.replace(`/c/${target.id}`);
  } catch (exception) {
    error.value = String(exception);
  }
});
</script>

<template>
  <v-container>
    <h1 class="text-h4 mb-6">Your contexts</h1>
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-row>
      <v-col v-for="context in contexts" :key="context.id" cols="12" md="6">
        <v-card :to="`/c/${context.id}`" hover>
          <v-card-title>{{ context.campaign_name }}</v-card-title>
          <v-card-subtitle>{{
            context.kind === "gm" ? "Game master" : context.character_name
          }}</v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>
    <v-alert v-if="!error && !contexts.length" type="info"
      >You are not yet a member of a campaign.</v-alert
    >
  </v-container>
</template>
