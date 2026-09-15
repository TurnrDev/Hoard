<template>
  <main class="container py-5">
    <section
      class="row justify-content-center"
      aria-labelledby="sign-in-heading"
    >
      <div class="col-12 col-sm-10 col-md-8 col-lg-5">
        <div class="border rounded-3 p-4 p-md-5">
          <header class="mb-4">
            <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
              Welcome back
            </p>
            <h1
              id="sign-in-heading"
              class="public-wordmark display-6"
            >
              Hoard
            </h1>
            <p class="mb-0 text-body-secondary">Campaign ledger and table tools</p>
          </header>
          <Message
            v-if="error"
            severity="error"
          >
            {{ error }}
          </Message>
          <form
            class="d-grid gap-3"
            @submit.prevent="submit"
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
              <span class="fw-semibold">Password</span>
              <InputText
                v-model="password"
                type="password"
                autocomplete="current-password"
                required
                fluid
              />
            </label>
            <Button
              type="submit"
              :loading="loading"
              :disabled="!csrfReady"
              label="Sign in"
            />
          </form>
        </div>
      </div>
    </section>
  </main>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { initialiseCsrf, login } from "@/api";

export default defineComponent({
  components: { Button, InputText, Message },
  data() {
    return { username: "", password: "", error: "", loading: false, csrfReady: false };
  },
  async mounted(): Promise<void> {
    try {
      await initialiseCsrf();
      this.csrfReady = true;
    } catch (exception) {
      this.error =
        exception instanceof Error
          ? exception.message
          : "Unable to initialise sign-in.";
    }
  },
  methods: {
    async submit(): Promise<void> {
      this.loading = true;
      this.error = "";
      try {
        if (!this.csrfReady) {
          await initialiseCsrf();
          this.csrfReady = true;
        }
        await login(this.username, this.password);
        await this.$router.push(
          typeof this.$route.query.next === "string" ? this.$route.query.next : "/",
        );
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to sign in.";
      } finally {
        this.loading = false;
      }
    },
  },
});
</script>
