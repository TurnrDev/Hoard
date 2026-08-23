<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  acceptInvite,
  initialiseCsrf,
  inspectInvite,
  login,
  registerAndAcceptInvite,
  type InviteDetails,
} from "../api";

const route = useRoute();
const router = useRouter();
const token = String(route.params.token);
const details = ref<InviteDetails>();
const username = ref("");
const email = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

onMounted(async () => {
  try {
    details.value = await inspectInvite(token);
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Invalid invitation.";
  }
});

async function accept(): Promise<void> {
  busy.value = true;
  try {
    const result = await acceptInvite(token);
    await router.replace(
      `/c/${result.context_id}/characters/${result.character_id}/build`,
    );
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "Unable to accept.";
  } finally {
    busy.value = false;
  }
}

async function register(): Promise<void> {
  busy.value = true;
  try {
    const result = await registerAndAcceptInvite(token, {
      username: username.value,
      email: email.value,
      password: password.value,
    });
    await initialiseCsrf();
    await login(username.value, password.value);
    await router.replace(
      `/c/${result.context_id}/characters/${result.character_id}/build`,
    );
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to register.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <v-container
    class="page-shell page-centered"
    style="max-width: 620px"
  >
    <v-card
      v-if="details"
      class="pa-4"
    >
      <v-card-title>Join {{ details.campaign_name }}</v-card-title>
      <v-card-subtitle>
        Invitation expires {{ new Date(details.expires_at).toLocaleString() }}
      </v-card-subtitle>
      <v-card-text>
        <v-alert
          v-if="error"
          type="error"
          class="mb-4"
        >
          {{ error }}
        </v-alert>
        <template v-if="details.authenticated">
          <p class="mb-4">Accept as {{ details.username }}.</p>
          <v-btn
            color="primary"
            block
            :loading="busy"
            @click="accept"
          >
            Accept invitation
          </v-btn>
        </template>
        <template v-else>
          <v-btn
            block
            variant="tonal"
            class="mb-6"
            :to="{ path: '/login', query: { next: route.fullPath } }"
          >
            Sign in to an existing account
          </v-btn>
          <div class="text-overline text-secondary mb-2">Create an account</div>
          <v-form @submit.prevent="register">
            <v-text-field
              v-model="username"
              label="Username"
              required
            />
            <v-text-field
              v-model="email"
              label="Email"
              type="email"
              required
            />
            <v-text-field
              v-model="password"
              label="Password"
              type="password"
              autocomplete="new-password"
              required
            />
            <v-btn
              color="primary"
              type="submit"
              block
              :loading="busy"
            >
              Create account and join
            </v-btn>
          </v-form>
        </template>
      </v-card-text>
    </v-card>
    <v-progress-circular
      v-else-if="!error"
      indeterminate
      color="primary"
    />
    <v-alert
      v-else
      type="error"
    >
      {{ error }}
    </v-alert>
  </v-container>
</template>
