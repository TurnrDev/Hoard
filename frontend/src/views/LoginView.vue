<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { initialiseCsrf, login } from "../api";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const csrfReady = ref(false);

onMounted(async () => {
  try {
    await initialiseCsrf();
    csrfReady.value = true;
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to initialise sign-in.";
  }
});

async function submit(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    if (!csrfReady.value) {
      await initialiseCsrf();
      csrfReady.value = true;
    }
    await login(username.value, password.value);
    await router.push("/");
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to sign in.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <v-container class="fill-height" style="max-width: 440px">
    <v-card class="pa-6" elevation="8">
      <v-card-title class="text-h4 text-primary font-weight-black"
        >Hoard</v-card-title
      >
      <v-card-subtitle>Campaign ledger and table tools</v-card-subtitle>
      <v-card-text class="pt-6">
        <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field
            v-model="username"
            label="Username"
            autocomplete="username"
            required
          />
          <v-text-field
            v-model="password"
            label="Password"
            type="password"
            autocomplete="current-password"
            required
          />
          <v-btn
            block
            color="primary"
            type="submit"
            :loading="loading"
            :disabled="!csrfReady"
            >Sign in</v-btn
          >
        </v-form>
      </v-card-text>
    </v-card>
  </v-container>
</template>
