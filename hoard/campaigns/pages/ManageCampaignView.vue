<template>
  <section aria-labelledby="manage-title">
    <header
      class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-5"
    >
      <div>
        <p class="text-uppercase fw-semibold small text-body-secondary mb-2">
          Game master
        </p>
        <h1
          id="manage-title"
          class="display-5 mb-0"
        >
          Manage campaign
        </h1>
      </div>
      <Button
        :as="'router-link'"
        :to="`/c/${campaignId}/gm`"
        label="GM console"
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
    <section
      class="border rounded-3 p-3 p-md-4 mb-4"
      aria-labelledby="invite-title"
    >
      <h2
        id="invite-title"
        class="h3"
      >
        Invite a player
      </h2>
      <form
        class="d-flex flex-column flex-md-row gap-2"
        @submit.prevent="invitePlayer"
      >
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
          class="flex-grow-1"
          placeholder="Optional email address"
        />
        <Button
          type="submit"
          :loading="busy"
          label="Create invitation"
        />
      </form>
      <Message
        v-if="invitationLink"
        severity="success"
        class="mt-3"
      >
        Invitation link:
        <a :href="invitationLink">{{ invitationLink }}</a>
      </Message>
    </section>
    <section
      class="border rounded-3 p-3 p-md-4 mb-4"
      aria-labelledby="party-xp-title"
    >
      <h2
        id="party-xp-title"
        class="h3"
      >
        Party XP
      </h2>
      <p class="text-body-secondary">
        Divide XP among this many players. Include players who do not have a DiceCloud
        sheet.
      </p>
      <form
        class="d-flex flex-column flex-sm-row align-items-sm-end gap-2"
        @submit.prevent="saveExperienceRecipientCount"
      >
        <label class="d-grid gap-2">
          <span class="fw-semibold">Players receiving XP</span>
          <InputNumber
            v-model="experienceRecipientCount"
            :min="1"
            :max="100"
            :use-grouping="false"
          />
        </label>
        <Button
          type="submit"
          :loading="recipientCountBusy"
          label="Save XP players"
        />
      </form>
    </section>
    <section aria-labelledby="players-title">
      <h2
        id="players-title"
        class="h3"
      >
        Players
      </h2>
      <ul class="list-group">
        <li
          v-for="character in characters"
          :key="character.id"
          class="list-group-item d-flex align-items-center justify-content-between gap-3"
        >
          <span>
            <strong>{{ character.name }}</strong>
            <span class="d-block small text-body-secondary">
              {{
                character.is_connected
                  ? "DiceCloud connected"
                  : "Awaiting DiceCloud connection"
              }}
            </span>
          </span>
          <Button
            :as="'router-link'"
            :to="`/c/${campaignId}/characters/${character.id}`"
            label="Manage link"
            outlined
          />
        </li>
      </ul>
    </section>
  </section>
</template>

<script lang="ts">
import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { defineComponent } from "vue";
import {
  createInvitation,
  getCampaign,
  setExperienceRecipientCount,
  type Character,
} from "@/api";
import { campaignRefreshRevision } from "@/realtime";

export default defineComponent({
  components: { Button, InputNumber, InputText, Message },
  data() {
    return {
      characters: [] as Character[],
      invitationEmail: "",
      invitationLink: "",
      experienceRecipientCount: 1,
      error: "",
      busy: false,
      recipientCountBusy: false,
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
    async load(): Promise<void> {
      try {
        const campaign = await getCampaign(this.campaignId);
        if (!campaign.is_game_master) {
          await this.$router.replace(`/c/${this.campaignId}`);
          return;
        }
        this.characters = campaign.characters;
        this.experienceRecipientCount = campaign.experience_recipient_count;
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to load campaign management.";
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
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to create invitation.";
      } finally {
        this.busy = false;
      }
    },
    async saveExperienceRecipientCount(): Promise<void> {
      this.recipientCountBusy = true;
      try {
        this.error = "";
        await setExperienceRecipientCount(
          this.campaignId,
          this.experienceRecipientCount,
        );
      } catch (exception) {
        this.error =
          exception instanceof Error
            ? exception.message
            : "Unable to save the XP player count.";
      } finally {
        this.recipientCountBusy = false;
      }
    },
  },
});
</script>
