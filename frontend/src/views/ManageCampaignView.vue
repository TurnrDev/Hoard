<template>
  <section aria-labelledby="management-title">
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-5"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Game Master only
        </p>
        <h1
          id="management-title"
          class="display-5 mb-0"
        >
          {{ campaign?.name }} management
        </h1>
      </div>
      <Button
        :as="'router-link'"
        :to="`/c/${campaignId}/gm`"
        icon="mdi mdi-arrow-left"
        label="GM desk"
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

    <div class="row g-4">
      <div class="col-12 col-xl-7">
        <section
          class="border rounded-3 p-3 p-md-4 h-100"
          aria-labelledby="members-heading"
        >
          <header class="mb-3">
            <h2
              id="members-heading"
              class="h3"
            >
              Members
            </h2>
          </header>
          <div class="d-grid gap-3">
            <form
              class="row g-2"
              @submit.prevent="invitePlayer"
            >
              <div class="col-12 col-md">
                <label
                  class="visually-hidden"
                  for="invitation-email"
                >
                  Email address
                </label>
                <InputText
                  id="invitation-email"
                  v-model="invitationEmail"
                  type="email"
                  placeholder="Email (optional)"
                  fluid
                />
              </div>
              <div class="col-12 col-md-auto">
                <Button
                  type="submit"
                  :loading="busy"
                  label="Invite player"
                />
              </div>
            </form>
            <Message
              v-if="invitationLink"
              severity="success"
            >
              <p class="fw-semibold mb-2">Shareable invitation link</p>
              <div class="d-flex flex-wrap align-items-center gap-2">
                <code class="text-break">{{ invitationLink }}</code>
                <Button
                  size="small"
                  label="Copy"
                  @click="copyInvite(invitationLink)"
                />
              </div>
            </Message>
            <ul class="list-group">
              <li
                v-for="member in members"
                :key="member.id"
                class="list-group-item d-flex align-items-center justify-content-between gap-3"
              >
                <div>
                  <strong>{{ member.username }}</strong>
                  <span class="d-block small text-body-secondary">
                    {{
                      member.is_active
                        ? member.is_game_master
                          ? "Game master"
                          : "Player"
                        : "Inactive"
                    }}
                  </span>
                </div>
                <Button
                  icon="mdi mdi-account-remove"
                  text
                  :disabled="!member.is_active"
                  :aria-label="`Deactivate ${member.username}`"
                  @click="deactivate(member)"
                />
              </li>
            </ul>
            <h3 class="h4 mt-2">Invitations</h3>
            <ul
              v-if="invitations.length"
              class="list-group"
            >
              <li
                v-for="invitation in invitations"
                :key="invitation.id"
                class="list-group-item d-flex align-items-center justify-content-between gap-3"
              >
                <div>
                  <strong>{{ invitation.email || "Shareable link" }}</strong>
                  <span class="d-block small text-body-secondary">
                    {{ displayIdentifier(invitation.status) }} · expires
                    <RelativeTime :value="invitation.expires_at" />
                  </span>
                </div>
                <div class="d-flex gap-1">
                  <Button
                    v-if="invitation.status === 'pending'"
                    icon="mdi mdi-email-sync-outline"
                    text
                    :aria-label="`Resend invitation to ${invitation.email || 'shareable link'}`"
                    @click="resend(invitation)"
                  />
                  <Button
                    v-if="invitation.status === 'pending'"
                    icon="mdi mdi-link-off"
                    text
                    :aria-label="`Revoke invitation to ${invitation.email || 'shareable link'}`"
                    @click="revoke(invitation)"
                  />
                </div>
              </li>
            </ul>
            <p
              v-else
              class="text-body-secondary mb-0"
            >
              No invitations have been created.
            </p>
          </div>
        </section>
      </div>
      <div class="col-12 col-xl-5">
        <div class="d-grid gap-4">
          <section
            class="border rounded-3 p-3 p-md-4"
            aria-labelledby="campaign-tools-heading"
          >
            <header>
              <h2
                id="campaign-tools-heading"
                class="h3"
              >
                Campaign tools
              </h2>
            </header>
            <div>
              <p class="text-body-secondary">
                Manage the campaign’s equipment in the dedicated compendium.
              </p>
              <Button
                :as="'router-link'"
                :to="`/c/${campaignId}/compendium`"
                icon="mdi mdi-book-open-variant"
                label="Open compendium"
              />
            </div>
          </section>
          <section
            class="border rounded-3 p-3 p-md-4"
            aria-labelledby="characters-heading"
          >
            <header>
              <h2
                id="characters-heading"
                class="h3"
              >
                NPCs
              </h2>
            </header>
            <div class="d-grid gap-3">
              <form
                class="row g-2"
                @submit.prevent="createNpc"
              >
                <div class="col-12">
                  <label
                    class="form-label"
                    for="npc-name"
                  >
                    Name
                  </label>
                  <InputText
                    id="npc-name"
                    v-model="characterName"
                    fluid
                  />
                </div>
                <div class="col-6">
                  <label
                    class="form-label"
                    for="npc-race"
                  >
                    Ancestry
                  </label>
                  <InputText
                    id="npc-race"
                    v-model="characterRace"
                    fluid
                  />
                </div>
                <div class="col-6">
                  <label
                    class="form-label"
                    for="npc-class"
                  >
                    Class
                  </label>
                  <InputText
                    id="npc-class"
                    v-model="characterClass"
                    fluid
                  />
                </div>
                <div class="col-12">
                  <Button
                    type="submit"
                    label="Create NPC"
                  />
                </div>
              </form>
              <ul
                v-if="characters.length"
                class="list-group"
              >
                <li
                  v-for="character in characters"
                  :key="character.id"
                  class="list-group-item d-flex align-items-center justify-content-between gap-3"
                >
                  <div>
                    <strong>{{ character.name }}</strong>
                    <span class="d-block small text-body-secondary">
                      {{
                        character.is_archived
                          ? "Archived"
                          : character.is_active
                            ? "Active"
                            : "Inactive"
                      }}
                    </span>
                  </div>
                  <Button
                    v-if="!character.is_archived"
                    icon="mdi mdi-archive"
                    text
                    :aria-label="`Archive ${character.name}`"
                    @click="archive(character)"
                  />
                </li>
              </ul>
              <p
                v-else
                class="text-body-secondary mb-0"
              >
                No NPCs have been created.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { defineComponent } from "vue";
import {
  archiveCharacter,
  createInvitation,
  createCharacter,
  getCampaign,
  removeMember,
  resendInvitation,
  revokeInvitation,
  type Campaign,
  type CampaignInvitation,
  type CampaignMember,
  type Character,
} from "../api";
import { campaignRefreshRevision } from "../realtime";
import { displayIdentifier } from "../display";
import RelativeTime from "../components/RelativeTime.vue";

export default defineComponent({
  components: { Button, InputText, Message, RelativeTime },
  data() {
    return {
      campaign: undefined as Campaign | undefined,
      members: [] as CampaignMember[],
      invitations: [] as CampaignInvitation[],
      characters: [] as Character[],
      invitationEmail: "",
      invitationLink: "",
      characterName: "",
      characterRace: "Human",
      characterClass: "Fighter",
      error: "",
      busy: false,
    };
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
    displayIdentifier,
    showSuccess(message: string): void {
      this.$toast.add({
        severity: "success",
        summary: message,
        life: 4_000,
      });
    },
    async load(): Promise<void> {
      try {
        const next = await getCampaign(this.campaignId);
        if (!next.is_game_master) {
          await this.$router.replace(`/c/${this.campaignId}`);
          return;
        }
        this.campaign = next;
        this.members = next.members;
        this.characters = next.characters.filter(
          (character) => !character.is_player_character,
        );
        this.invitations = next.invitations;
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load campaign management.";
      }
    },
    async createNpc(): Promise<void> {
      if (!this.characterName.trim()) {
        return;
      }
      try {
        await createCharacter(this.campaignId, {
          name: this.characterName.trim(),
          race: this.characterRace,
          character_class: this.characterClass,
          strength: 10,
          dexterity: 10,
          constitution: 10,
          intelligence: 10,
          wisdom: 10,
          charisma: 10,
          is_npc: true,
        });
        this.characterName = "";
        await this.load();
        this.showSuccess("NPC created.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to create NPC.";
      }
    },
    async archive(character: Character): Promise<void> {
      try {
        await archiveCharacter(this.campaignId, character.id);
        await this.load();
        this.showSuccess(`${character.name} archived.`);
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to archive character.";
      }
    },
    async invitePlayer(): Promise<void> {
      this.busy = true;
      try {
        const invitation = await createInvitation(
          this.campaignId,
          this.invitationEmail.trim(),
        );
        this.invitationEmail = "";
        this.invitationLink = invitation.link ?? "";
        await this.load();
        this.showSuccess("Invitation created.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to invite player.";
      } finally {
        this.busy = false;
      }
    },
    async copyInvite(link: string): Promise<void> {
      try {
        await navigator.clipboard.writeText(link);
        this.showSuccess("Invitation link copied.");
      } catch {
        this.error = "Unable to copy the invitation link.";
      }
    },
    async resend(invitation: CampaignInvitation): Promise<void> {
      try {
        const updated = await resendInvitation(this.campaignId, invitation.id);
        this.invitationLink = updated.link ?? "";
        await this.load();
        this.showSuccess("Invitation resent.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to resend.";
      }
    },
    async revoke(invitation: CampaignInvitation): Promise<void> {
      try {
        await revokeInvitation(this.campaignId, invitation.id);
        await this.load();
        this.showSuccess("Invitation revoked.");
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to revoke.";
      }
    },
    async deactivate(member: CampaignMember): Promise<void> {
      try {
        await removeMember(this.campaignId, member.id);
        await this.load();
        this.showSuccess(`${member.username} deactivated.`);
      } catch (exception) {
        this.error =
          exception instanceof Error ? exception.message : "Unable to remove member.";
      }
    },
  },
});
</script>
