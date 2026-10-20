<template>
  <section aria-labelledby="characters-title">
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-5"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Campaign roster
        </p>
        <h1
          id="characters-title"
          class="display-5 mb-0"
        >
          Characters
        </h1>
      </div>
      <Button
        :as="'router-link'"
        :to="`/c/${campaignId}`"
        icon="mdi mdi-home-variant-outline"
        label="Campaign home"
        outlined
      />
    </header>
    <Message
      v-if="error"
      severity="error"
      closable
      @close="error = ''"
    >
      {{ error }}
    </Message>
    <ul
      v-if="characters.length"
      class="list-unstyled row g-4"
    >
      <li
        v-for="character in characters"
        :key="character.id"
        class="col-12 col-md-6 col-xl-4"
      >
        <article class="border rounded-3 p-3 p-md-4 h-100 d-flex flex-column">
          <header class="d-flex align-items-center gap-3 mb-3">
            <CharacterAvatar
              :character="character"
              size="preview"
            />
            <div>
              <h2 class="h3 mb-1">{{ character.name }}</h2>
              <p class="text-body-secondary mb-0">
                {{
                  character.is_connected
                    ? `${character.race || "Unknown race"} · ${character.class || "Unknown class"}`
                    : "DiceCloud sheet not connected"
                }}
              </p>
            </div>
          </header>
          <p class="small text-body-secondary mt-auto mb-0">
            {{ character.is_active ? "Active player" : "Inactive player" }}
            <span v-if="character.profile?.stale">· Showing cached data</span>
          </p>
          <footer class="mt-3">
            <Button
              :as="'router-link'"
              :to="`/c/${campaignId}/characters/${character.id}`"
              :label="
                character.is_connected ? 'View DiceCloud sheet' : 'Connect DiceCloud'
              "
              outlined
            />
          </footer>
        </article>
      </li>
    </ul>
    <Message
      v-else
      severity="info"
    >
      No player contexts are currently visible in this campaign.
    </Message>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Message from "primevue/message";
import { defineComponent } from "vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import { getCampaign, type Character } from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: { Button, CharacterAvatar, Message },
  data() {
    return { characters: [] as Character[], error: "" };
  },
  computed: {
    campaignId(): number {
      return Number(this.$route.params.id);
    },
    campaignRefresh(): number {
      return campaignRefreshRevision.value;
    },
  },
  watch: {
    campaignRefresh(): void {
      void this.load();
    },
  },
  mounted() {
    void this.load();
  },
  methods: {
    async load(): Promise<void> {
      try {
        this.characters = (await getCampaign(this.campaignId)).characters;
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load characters.";
      }
    },
  },
});
</script>
