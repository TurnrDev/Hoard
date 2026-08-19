<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { contextPath, defaultContext } from "../context";

const route = useRoute();
const router = useRouter();
const error = ref("");

onMounted(async () => {
  const context = await defaultContext(Number(route.params.id));
  if (context) await router.replace(contextPath(context));
  else error.value = "You do not have an active role in this campaign.";
});
</script>

<template>
  <v-container class="page-shell page-centered">
    <v-progress-circular v-if="!error" indeterminate color="primary" />
    <v-alert v-else type="warning">{{ error }}</v-alert>
  </v-container>
</template>
