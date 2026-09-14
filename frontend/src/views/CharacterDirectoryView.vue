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
      @click:close="error = ''"
    >
      {{ error }}
    </Message>
    <Message
      v-if="campaign?.is_game_master && campaign.incomplete_level_ups.length"
      severity="error"
      class="mb-4"
    >
      {{ campaign.incomplete_level_ups.map((row) => row.character_name).join(", ") }}
      still need to complete level {{ campaign.level }}.
    </Message>
    <ul class="list-unstyled row g-4">
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
              <h2 class="h3 mb-1">{{ character.name }}</h2>
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
              {{ character.experience }} XP · {{ character.inventory.length }} inventory
              entries
            </p>
          </div>
          <footer class="d-flex flex-wrap gap-2 mt-3">
            <Button
              :as="'router-link'"
              :to="`/c/${campaignId}/characters/${character.id}`"
              label="View sheet"
              outlined
            />
            <Button
              v-if="ownIds.has(character.id)"
              severity="primary"
              :as="'router-link'"
              :to="actingPath(character)"
              label="Open profile"
            ></Button>
          </footer>
        </article>
      </li>
    </ul>
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
            class="list-group-item list-group-item-action d-flex justify-content-between gap-3"
            :to="`/c/${campaignId}/characters/${character.id}`"
          >
            <CharacterAvatar
              :character="character"
              size="rail"
            />
            <span>{{ character.name }}</span>
            <span class="text-body-secondary">
              {{ character.race }} · {{ character.class }}
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
import CharacterAvatar from "../components/CharacterAvatar.vue";
import { formatGoldValue } from "../money";
import {
  getCampaign,
  getCharacters,
  getMyCharacters,
  type Campaign,
  type Character,
} from "../api";
import { campaignRefreshRevision } from "../realtime";

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
        const [nextCampaign, visible, own] = await Promise.all([
          getCampaign(this.campaignId),
          getCharacters(this.campaignId),
          getMyCharacters(this.campaignId),
        ]);
        this.campaign = nextCampaign;
        this.characters = visible;
        this.ownIds = new Set(
          own
            .filter((character) => character.is_active && !character.is_archived)
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
