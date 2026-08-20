<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  addMember,
  archiveCharacter,
  createCharacter,
  getCharacters,
  getCampaign,
  getMembers,
  removeMember,
  updateMember,
  type Campaign,
  type CampaignMember,
  type Character,
} from "../api";

const route = useRoute();
const router = useRouter();
const campaignId = Number(route.params.id);
const campaign = ref<Campaign>();
const members = ref<CampaignMember[]>([]);
const characters = ref<Character[]>([]);
const username = ref("");
const makeGm = ref(false);
const characterName = ref("");
const characterRace = ref("Human");
const characterClass = ref("Fighter");
const error = ref("");
const busy = ref(false);

async function load(): Promise<void> {
  try {
    const next = await getCampaign(campaignId);
    if (!next.is_game_master) {
      await router.replace(`/c/${campaignId}`);
      return;
    }
    campaign.value = next;
    [members.value, characters.value] = await Promise.all([
      getMembers(campaignId),
      getCharacters(campaignId),
    ]);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load campaign management.";
  }
}

async function createNpc(): Promise<void> {
  if (!characterName.value.trim()) return;
  try {
    await createCharacter(campaignId, {
      name: characterName.value.trim(),
      race: characterRace.value,
      character_class: characterClass.value,
      strength: 10,
      dexterity: 10,
      constitution: 10,
      intelligence: 10,
      wisdom: 10,
      charisma: 10,
      is_npc: true,
    });
    characterName.value = "";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to create NPC.";
  }
}

async function archive(character: Character): Promise<void> {
  try {
    await archiveCharacter(campaignId, character.id);
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to archive character.";
  }
}

async function createMember(): Promise<void> {
  if (!username.value.trim()) return;
  busy.value = true;
  try {
    await addMember(campaignId, username.value.trim(), makeGm.value);
    username.value = "";
    makeGm.value = false;
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to add member.";
  } finally {
    busy.value = false;
  }
}

async function toggleGm(member: CampaignMember): Promise<void> {
  try {
    await updateMember(campaignId, member.id, !member.is_game_master);
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to update member.";
  }
}

async function deactivate(member: CampaignMember): Promise<void> {
  try {
    await removeMember(campaignId, member.id);
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to remove member.";
  }
}

onMounted(load);
</script>

<template>
  <v-container style="max-width: 1100px">
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4">{{ campaign?.name }} management</h1>
      <v-btn
        :to="`/c/${campaignId}`"
        prepend-icon="mdi-arrow-left"
      >
        Campaign
      </v-btn>
    </div>
    <v-alert
      v-if="error"
      type="error"
      closable
      @click:close="error = ''"
    >
      {{ error }}
    </v-alert>

    <v-row>
      <v-col
        cols="12"
        md="7"
      >
        <v-card>
          <v-card-title>Members</v-card-title>
          <v-card-text>
            <v-form
              class="d-flex ga-2 mb-4"
              @submit.prevent="createMember"
            >
              <v-text-field
                v-model="username"
                label="Username"
                hide-details
              />
              <v-checkbox
                v-model="makeGm"
                label="GM"
                hide-details
              />
              <v-btn
                type="submit"
                :loading="busy"
              >
                Add
              </v-btn>
            </v-form>
            <v-list>
              <v-list-item
                v-for="member in members"
                :key="member.id"
              >
                <v-list-item-title>{{ member.username }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{
                    member.is_active
                      ? member.is_game_master
                        ? "Game master"
                        : "Player"
                      : "Inactive"
                  }}
                </v-list-item-subtitle>
                <template #append>
                  <v-btn
                    icon="mdi-shield-account"
                    variant="text"
                    :disabled="!member.is_active"
                    @click="toggleGm(member)"
                  />
                  <v-btn
                    icon="mdi-account-remove"
                    variant="text"
                    :disabled="!member.is_active"
                    @click="deactivate(member)"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        md="5"
      >
        <v-card>
          <v-card-title>Campaign tools</v-card-title>
          <v-card-text>
            <p class="mb-4">
              Manage the campaign’s equipment in the dedicated compendium.
            </p>
            <v-btn
              :to="`/c/${campaignId}/compendium`"
              prepend-icon="mdi-book-open-variant"
            >
              Open compendium
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12">
        <v-card>
          <v-card-title>Characters</v-card-title>
          <v-card-text>
            <v-form
              class="d-flex flex-wrap ga-2 mb-4"
              @submit.prevent="createNpc"
            >
              <v-text-field
                v-model="characterName"
                label="NPC name"
                hide-details
              />
              <v-text-field
                v-model="characterRace"
                label="Race"
                hide-details
              />
              <v-text-field
                v-model="characterClass"
                label="Class"
                hide-details
              />
              <v-btn type="submit">Create NPC</v-btn>
            </v-form>
            <v-list density="compact">
              <v-list-item
                v-for="character in characters"
                :key="character.id"
                :title="character.name"
                :subtitle="
                  character.is_archived
                    ? 'Archived'
                    : character.is_active
                      ? 'Active'
                      : 'Inactive'
                "
              >
                <template #append>
                  <v-btn
                    v-if="!character.is_archived"
                    icon="mdi-archive"
                    variant="text"
                    @click="archive(character)"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
