<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  archiveCharacter,
  createInvitation,
  createCharacter,
  getCharacters,
  getCampaign,
  getInvitations,
  getMembers,
  removeMember,
  resendInvitation,
  revokeInvitation,
  type Campaign,
  type CampaignInvitation,
  type CampaignMember,
  type Character,
} from "../api";
import { useCampaignRefresh } from "../realtime";
import { displayIdentifier } from "../display";

const route = useRoute();
const router = useRouter();
const campaignId = Number(route.params.id);
const campaign = ref<Campaign>();
const members = ref<CampaignMember[]>([]);
const invitations = ref<CampaignInvitation[]>([]);
const characters = ref<Character[]>([]);
const invitationEmail = ref("");
const invitationLink = ref("");
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
    [members.value, characters.value, invitations.value] = await Promise.all([
      getMembers(campaignId),
      getCharacters(campaignId),
      getInvitations(campaignId),
    ]);
  } catch (exception) {
    error.value =
      exception instanceof Error
        ? exception.message
        : "Unable to load campaign management.";
  }
}

async function createNpc(): Promise<void> {
  if (!characterName.value.trim()) {
    return;
  }
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

async function invitePlayer(): Promise<void> {
  busy.value = true;
  try {
    const invitation = await createInvitation(campaignId, invitationEmail.value.trim());
    invitationEmail.value = "";
    invitationLink.value = invitation.link ?? "";
    await load();
  } catch (exception) {
    error.value =
      exception instanceof Error ? exception.message : "Unable to invite player.";
  } finally {
    busy.value = false;
  }
}

async function copyInvite(link: string): Promise<void> {
  await navigator.clipboard.writeText(link);
}

async function resend(invitation: CampaignInvitation): Promise<void> {
  try {
    const updated = await resendInvitation(campaignId, invitation.id);
    invitationLink.value = updated.link ?? "";
    await load();
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "Unable to resend.";
  }
}

async function revoke(invitation: CampaignInvitation): Promise<void> {
  try {
    await revokeInvitation(campaignId, invitation.id);
    await load();
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "Unable to revoke.";
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
useCampaignRefresh(load);
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
              @submit.prevent="invitePlayer"
            >
              <v-text-field
                v-model="invitationEmail"
                label="Email (optional)"
                type="email"
                hide-details
              />
              <v-btn
                type="submit"
                :loading="busy"
              >
                Invite player
              </v-btn>
            </v-form>
            <v-alert
              v-if="invitationLink"
              type="success"
              class="mb-4"
            >
              <div class="text-caption mb-1">Shareable invitation link</div>
              <div class="d-flex align-center ga-2">
                <code class="text-truncate">{{ invitationLink }}</code>
                <v-btn
                  size="small"
                  @click="copyInvite(invitationLink)"
                >
                  Copy
                </v-btn>
              </div>
            </v-alert>
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
                    icon="mdi-account-remove"
                    variant="text"
                    :disabled="!member.is_active"
                    :aria-label="`Deactivate ${member.username}`"
                    @click="deactivate(member)"
                  />
                </template>
              </v-list-item>
            </v-list>
            <div class="text-overline text-secondary mt-5">Invitations</div>
            <v-list density="compact">
              <v-list-item
                v-for="invitation in invitations"
                :key="invitation.id"
                :title="invitation.email || 'Shareable link'"
                :subtitle="`${displayIdentifier(invitation.status)} · expires ${new Date(invitation.expires_at).toLocaleString()}`"
              >
                <template #append>
                  <v-btn
                    v-if="invitation.status === 'pending'"
                    icon="mdi-email-sync-outline"
                    variant="text"
                    :aria-label="`Resend invitation to ${invitation.email || 'shareable link'}`"
                    @click="resend(invitation)"
                  />
                  <v-btn
                    v-if="invitation.status === 'pending'"
                    icon="mdi-link-off"
                    variant="text"
                    :aria-label="`Revoke invitation to ${invitation.email || 'shareable link'}`"
                    @click="revoke(invitation)"
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
                    :aria-label="`Archive ${character.name}`"
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
