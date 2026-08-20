<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getContexts } from "../api";

const route = useRoute();
const router = useRouter();
const error = ref("");

onMounted(async () => {
  const context = (await getContexts()).find(
    (candidate) => candidate.id === Number(route.params.id),
  );
  if (!context) {
    error.value = "This context is no longer available.";
    return;
  }
  await router.replace(
    context.kind === "gm"
      ? `/c/${context.id}/gm`
      : `/c/${context.id}/characters/${context.character_id}`,
  );
});
</script>

<template>
  <v-container class="page-shell page-centered">
    <v-progress-circular
      v-if="!error"
      indeterminate
      color="primary"
    />
    <v-alert
      v-else
      type="warning"
    >
      {{ error }}
    </v-alert>
  </v-container>
</template>
