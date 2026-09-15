<template>
  <main
    class="container min-vh-100 d-flex align-items-center justify-content-center py-5"
  >
    <div class="text-center">
      <ProgressSpinner
        v-if="!error"
        aria-label="Loading campaign"
      />
      <Message
        v-else
        severity="warn"
      >
        {{ error }}
      </Message>
    </div>
  </main>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import { getContexts } from "@/api";

export default defineComponent({
  components: { Message, ProgressSpinner },
  data() {
    return { error: "" };
  },
  async mounted(): Promise<void> {
    try {
      const context = (await getContexts()).find(
        (candidate) => candidate.id === Number(this.$route.params.id),
      );

      if (!context) {
        this.error = "This context is no longer available.";
        return;
      }

      if (context.kind === "gm") {
        await this.$router.replace(`/c/${context.id}/gm`);
        return;
      }

      if (!context.character_id) {
        this.error = "This player context does not have a character.";
        return;
      }

      await this.$router.replace(`/c/${context.id}/characters/${context.character_id}`);
    } catch (exception) {
      this.error =
        exception instanceof Error
          ? exception.message
          : "Unable to open this campaign.";
    }
  },
});
</script>
