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
      v-if="playerCharacters.length"
      class="list-unstyled row g-4"
    >
      <li
        v-for="character in playerCharacters"
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
              <h2 class="h3 mb-1">
                {{ character.name }}
              </h2>
              <p class="text-body-secondary mb-0">
                {{ character.race }} · {{ character.class }}
              </p>
            </div>
          </header>
          <div class="mt-auto">
            <p class="h4 tabular-nums">
              {{ formatGoldValue(character.money.gold_value) }} ¤
            </p>
            <p class="small text-body-secondary tabular-nums">
              {{ character.experience.toLocaleString() }} XP
            </p>
          </div>
          <footer class="d-flex flex-wrap gap-2 mt-3">
            <Button
              v-if="ownIds.has(character.id)"
              severity="primary"
              :as="'router-link'"
              :to="actingPath(character)"
              :label="`Play as ${character.name}`"
            />
            <Button
              v-else
              :as="'router-link'"
              :to="`/c/${campaignId}/characters/${character.id}`"
              label="View sheet"
              outlined
            />
          </footer>
        </article>
      </li>
    </ul>
    <p
      v-else-if="campaign"
      class="border rounded-3 p-4 text-body-secondary"
    >
      No player characters are currently visible in this campaign.
    </p>
    <section
      v-if="campaign?.is_game_master && hasNpcs"
      class="mt-5"
    >
      <header class="mb-3">
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Game Master only
        </p>
        <h2 class="h3">NPCs</h2>
      </header>
      <ul class="list-group">
        <li
          v-for="character in characters.filter(
            (candidate) => !candidate.is_player_character,
          )"
          :key="character.id"
        >
          <RouterLink
            class="list-group-item list-group-item-action d-flex align-items-center gap-3"
            :to="`/c/${campaignId}/characters/${character.id}`"
          >
            <CharacterAvatar
              :character="character"
              size="rail"
            />
            <span class="d-grid">
              <strong>{{ character.name }}</strong>
              <span class="text-body-secondary">
                {{ character.race }} · {{ character.class }}
              </span>
            </span>
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import Message from "primevue/message";
import { defineComponent } from "vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import { formatGoldValue } from "@/campaigns/money";
import { getCampaign, type Campaign, type Character } from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: { Button, CharacterAvatar, Message },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      characters: [] as Character[],
      ownIds: new Set<number>(),
      error: "",
    };
  },
  computed: {
    campaignId(): number {
      return Number(this.$route.params.id);
    },
    playerCharacters(): Character[] {
      return this.characters.filter((character) => character.is_player_character);
    },
    hasNpcs(): boolean {
      return this.characters.some((character) => !character.is_player_character);
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
    formatGoldValue,
    async load(): Promise<void> {
      try {
        const nextCampaign = await getCampaign(this.campaignId);

        this.campaign = nextCampaign;
        this.characters = nextCampaign.characters;
        this.ownIds = new Set(
          nextCampaign.characters
            .filter((character) => character.is_active)
            .filter((character) => character.context_id === this.campaignId)
            .map((character) => character.id),
        );
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to load characters.";
      }
    },
    actingPath(character: Character): string {
      return character.context_id ? `/c/${character.context_id}` : "";
    },
  },
});
</script>
