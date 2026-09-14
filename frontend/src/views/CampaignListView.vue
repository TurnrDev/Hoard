<template>
  <main class="container py-4 py-md-5">
    <header class="mb-5">
      <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
        Choose a table
      </p>
      <h1 class="display-5 mb-0">Your campaigns</h1>
    </header>
    <Message
      v-if="error"
      severity="error"
    >
      {{ error }}
    </Message>
    <ul class="list-unstyled row g-3">
      <li
        v-for="context in contexts"
        :key="context.id"
        class="col-12 col-md-6 col-xl-4"
      >
        <RouterLink
          :to="contextPath(context)"
          class="d-block h-100 border rounded-3 p-4 text-decoration-none text-body"
        >
          <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
            {{ context.kind === "gm" ? "Game Master" : "Player" }}
          </p>
          <h2 class="h3">{{ context.campaign_name }}</h2>
          <p class="mb-0 text-body-secondary">
            {{ context.kind === "gm" ? "Game master" : context.character_name }}
          </p>
        </RouterLink>
      </li>
    </ul>
    <Message
      v-if="!error && !contexts.length"
      severity="info"
    >
      You are not yet a member of a campaign.
    </Message>
  </main>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Message from "primevue/message";
import { getContexts, type CampaignContext } from "../api";
import { contextPath } from "../context";

export default defineComponent({
  components: { Message },
  data() {
    return { contexts: [] as CampaignContext[], error: "" };
  },
  async mounted(): Promise<void> {
    try {
      this.contexts = await getContexts();
      const saved = Number(localStorage.getItem("hoard:last-context"));
      const target =
        this.contexts.find((context) => context.id === saved) ??
        (this.contexts.length === 1 ? this.contexts[0] : undefined);
      if (target) {
        await this.$router.replace(contextPath(target));
      }
    } catch (exception) {
      this.error = String(exception);
    }
  },
  methods: {
    contextPath,
  },
});
</script>
