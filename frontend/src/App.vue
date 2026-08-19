<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { logout } from "./api";

const router = useRouter();
const busy = ref(false);

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
      <v-btn to="/campaigns" prepend-icon="mdi-map" variant="text"
        >Campaigns</v-btn
      >
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
