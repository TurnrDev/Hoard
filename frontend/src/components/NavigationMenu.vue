<script setup lang="ts">
import { contextPath, type ActingContext } from "../context";

defineProps<{
  contextId: number;
  activeContext?: ActingContext;
}>();
</script>

<template>
  <v-list
    v-if="contextId"
    nav
    density="comfortable"
  >
    <v-list-item
      prepend-icon="mdi-home-variant-outline"
      title="Home"
      :to="activeContext ? contextPath(activeContext) : `/c/${contextId}`"
    />
    <v-list-item
      prepend-icon="mdi-account-group-outline"
      title="Characters"
      :to="`/c/${contextId}/characters`"
    />
    <v-list-item
      prepend-icon="mdi-book-open-variant-outline"
      title="Compendium"
      :to="`/c/${contextId}/compendium`"
    />
    <v-list-item
      prepend-icon="mdi-notebook-outline"
      title="Ledger"
      :to="`/c/${contextId}/ledger`"
    />
    <v-list-item
      v-if="activeContext?.kind === 'gm'"
      prepend-icon="mdi-cog-outline"
      title="Manage"
      :to="`/c/${contextId}/manage`"
    />
  </v-list>
</template>
