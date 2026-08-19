<script setup lang="ts">
import { contextPath, type ActingContext } from "../context";

const props = defineProps<{
  campaignId: number;
  activeContext?: ActingContext;
}>();
</script>

<template>
  <v-list v-if="campaignId" nav density="comfortable">
    <v-list-item
      prepend-icon="mdi-home-variant-outline"
      title="Home"
      :to="activeContext ? contextPath(activeContext) : `/c/${campaignId}`"
    />
    <v-list-item
      prepend-icon="mdi-account-group-outline"
      title="Characters"
      :to="`/c/${campaignId}/characters`"
    />
    <v-list-item
      prepend-icon="mdi-book-open-variant-outline"
      title="Compendium"
      :to="`/c/${campaignId}/compendium`"
    />
    <v-list-item
      prepend-icon="mdi-notebook-outline"
      title="Ledger"
      :to="`/c/${campaignId}/ledger`"
    />
    <v-list-item
      v-if="activeContext?.kind === 'gm'"
      prepend-icon="mdi-cog-outline"
      title="Manage"
      :to="`/c/${campaignId}/manage`"
    />
  </v-list>
</template>
