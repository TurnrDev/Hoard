<template>
  <main class="container py-5">
    <section
      v-if="details"
      class="row justify-content-center"
      aria-labelledby="invite-heading"
    >
      <div class="col-12 col-md-9 col-lg-6">
        <div class="border rounded-3 p-4 p-md-5">
          <header class="mb-4">
            <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
              Campaign invitation
            </p>
            <h1
              id="invite-heading"
              class="display-6"
            >
              Join {{ details.campaign_name }}
            </h1>
            <p class="mb-0 text-body-secondary">
              Invitation expires
              <RelativeTime :value="details.expires_at" />
            </p>
          </header>
          <Message
            v-if="error"
            severity="error"
          >
            {{ error }}
          </Message>
          <template v-if="details.authenticated">
            <p>Accept as {{ details.username }}.</p>
            <Button
              :loading="busy"
              label="Accept invitation"
              @click="accept"
            />
          </template>
          <template v-else>
            <RouterLink :to="{ path: '/login', query: { next: $route.fullPath } }">
              Sign in to an existing account
            </RouterLink>
            <h2 class="h4 mt-4">Create an account</h2>
            <form
              class="d-grid gap-3"
              @submit.prevent="register"
            >
              <label class="d-grid gap-2">
                <span class="fw-semibold">Username</span>
                <InputText
                  v-model="username"
                  autocomplete="username"
                  required
                  fluid
                />
              </label>
              <label class="d-grid gap-2">
                <span class="fw-semibold">Email</span>
                <InputText
                  v-model="email"
                  type="email"
                  autocomplete="email"
                  required
                  fluid
                />
              </label>
              <label class="d-grid gap-2">
                <span class="fw-semibold">Password</span>
                <InputText
                  v-model="password"
                  type="password"
                  autocomplete="new-password"
                  required
                  fluid
                />
              </label>
              <Button
                type="submit"
                :loading="busy"
                label="Create account and join"
              />
            </form>
          </template>
        </div>
      </div>
    </section>
    <ProgressSpinner
      v-else-if="!error"
      aria-label="Loading invitation"
    />
    <Message
      v-else
      severity="error"
    >
      {{ error }}
    </Message>
  </main>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import RelativeTime from "@/components/RelativeTime.vue";
import {
  acceptInvite,
  initialiseCsrf,
  inspectInvite,
  login,
  registerAndAcceptInvite,
  type InviteDetails,
} from "@/api";
import { contexts, rememberContext } from "@/campaigns/context";

export default defineComponent({
  components: { Button, InputText, Message, ProgressSpinner, RelativeTime },
  emits: ["contexts-changed"],
  data() {
    return {
      details: undefined as InviteDetails | undefined,
      username: "",
      email: "",
      password: "",
      error: "",
      busy: false,
    };
  },
  computed: {
    token(): string {
      return String(this.$route.params.token);
    },
  },
  async mounted(): Promise<void> {
    try {
      this.details = await inspectInvite(this.token);
    } catch (exception) {
      this.error =
        exception instanceof Error ? exception.message : "Invalid invitation.";
    }
  },
  methods: {
    async accept(): Promise<void> {
      this.busy = true;
      try {
        const result = await acceptInvite(this.token);
        await this.openCharacterProfile(result);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to accept.";
      } finally {
        this.busy = false;
      }
    },
    async register(): Promise<void> {
      this.busy = true;
      try {
        const result = await registerAndAcceptInvite(this.token, {
          username: this.username,
          email: this.email,
          password: this.password,
        });
        await initialiseCsrf();
        await login(this.username, this.password);
        await this.openCharacterProfile(result);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to register.";
      } finally {
        this.busy = false;
      }
    },
    async openCharacterProfile(result: {
      context_id: number;
      character_id: number;
    }): Promise<void> {
      const availableContexts = await contexts();
      const context = availableContexts.find(
        (candidate) => candidate.id === result.context_id,
      );

      if (context) {
        rememberContext(context);
      }

      this.$emit("contexts-changed");
      await this.$router.replace(
        `/c/${result.context_id}/characters/${result.character_id}`,
      );
    },
  },
});
</script>
