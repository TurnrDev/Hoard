<template>
  <main
    v-if="isPublicRoute"
    class="min-vh-100"
  >
    <router-view @contexts-changed="loadContexts" />
  </main>

  <div
    v-else
    class="campaign-shell min-vh-100"
  >
    <a
      class="visually-hidden-focusable skip-link border bg-body text-body px-3 py-2"
      href="#main-content"
    >
      Skip to main content
    </a>

    <header class="campaign-header border-bottom">
      <div class="d-flex align-items-center gap-2">
        <Button
          class="d-lg-none"
          icon="mdi mdi-menu"
          text
          rounded
          aria-label="Open campaign navigation"
          @click="navigationOpen = true"
        />
        <RouterLink
          class="campaign-header__wordmark fw-bold text-decoration-none"
          :to="activeContext ? contextPath(activeContext) : '/'"
        >
          HOARD
        </RouterLink>
      </div>

      <p
        v-if="campaign"
        class="campaign-header__campaign mb-0 text-center"
        :title="campaign.calendar.era_name"
      >
        <span>{{ campaign.name }}</span>
        <span aria-hidden="true">{{ " · " }}</span>
        <span>{{ formatCampaignDate(campaign.calendar) }}</span>
      </p>

      <div class="d-flex align-items-center justify-content-end gap-2">
        <Button
          class="p-1"
          text
          rounded
          aria-label="Open account and campaign menu"
          aria-haspopup="menu"
          aria-controls="account-menu"
          @click="toggleAccountMenu"
        >
          <CharacterAvatar
            v-if="activeCharacter"
            :character="activeCharacter"
            size="menu"
          />
          <span
            v-else
            class="mdi mdi-account-circle-outline fs-3"
            aria-hidden="true"
          />
        </Button>
        <TieredMenu
          id="account-menu"
          ref="accountMenu"
          :model="accountMenuItems"
          popup
        />
      </div>
    </header>

    <Drawer
      v-model:visible="navigationOpen"
      header="Campaign navigation"
      position="left"
    >
      <CampaignNavigation
        v-if="activeContext"
        :context-id="contextId"
        :active-context="activeContext"
      />
    </Drawer>

    <div
      class="campaign-layout"
      :class="{ 'campaign-layout--rail-expanded': partyRailExpanded }"
    >
      <aside class="campaign-navigation-panel d-none d-lg-block border-end p-3">
        <CampaignNavigation
          v-if="activeContext"
          :context-id="contextId"
          :active-context="activeContext"
        />
      </aside>

      <section
        v-if="campaign && activeContext"
        class="campaign-rail-panel border-start"
      >
        <PartyRail
          :campaign="campaign"
          :members="members"
          :active-context="activeContext"
          :expanded="partyRailExpanded"
          @toggle="partyRailExpanded = !partyRailExpanded"
        />
      </section>

      <main
        id="main-content"
        class="campaign-main container-fluid py-4 py-lg-5"
      >
        <p
          v-if="activeContext"
          class="campaign-main__context d-lg-none text-body-secondary small mb-4"
        >
          {{ contextLabel }}
        </p>
        <Message
          v-if="incompleteLevelUps.length"
          class="mb-4"
          severity="warn"
        >
          <strong>Level-up incomplete.</strong>
          {{ incompleteLevelUps.join(", ") }} still need to finish the approved group
          level-up.
        </Message>
        <router-view @contexts-changed="loadContexts" />
      </main>
    </div>
  </div>
</template>

<script lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import type { MenuItem } from "primevue/menuitem";
import Message from "primevue/message";
import TieredMenu from "primevue/tieredmenu";
import { defineComponent } from "vue";
import {
  getCampaign,
  logout,
  type Campaign,
  type CampaignMember,
  type Character,
} from "./api";
import { formatCampaignDate } from "./calendar";
import CampaignNavigation from "./components/CampaignNavigation.vue";
import CharacterAvatar from "./components/CharacterAvatar.vue";
import PartyRail from "./components/PartyRail.vue";
import { contextPath, contexts, rememberContext, type ActingContext } from "./context";
import {
  campaignRefreshRevision,
  connectCampaignRealtime,
  disconnectCampaignRealtime,
  subscribeCampaignChanges,
  subscribeCampaignPresence,
  subscribeCampaignReconnect,
} from "./realtime";
import {
  applyThemePreferences,
  readThemePreferences,
  type ThemePreferences,
} from "./theme";

export default defineComponent({
  components: {
    CampaignNavigation,
    CharacterAvatar,
    Drawer,
    Message,
    PartyRail,
    Button,
    TieredMenu,
  },
  data() {
    const themePreferences = readThemePreferences();

    return {
      navigationOpen: false,
      partyRailExpanded: false,
      busy: false,
      colourMode: themePreferences.colourMode,
      palette: themePreferences.palette,
      availableContexts: [] as ActingContext[],
      campaign: undefined as Campaign | undefined,
      members: [] as CampaignMember[],
      incompleteLevelUps: [] as string[],
      unsubscribeCampaignChanges: undefined as (() => void) | undefined,
      unsubscribeCampaignReconnect: undefined as (() => void) | undefined,
      unsubscribeCampaignPresence: undefined as (() => void) | undefined,
      presenceSweepTimer: undefined as number | undefined,
    };
  },
  computed: {
    contextId(): number {
      return Number(this.$route.params.id);
    },
    isPublicRoute(): boolean {
      return this.$route.path === "/login" || this.$route.path.startsWith("/invites/");
    },
    activeContext(): ActingContext | undefined {
      return this.availableContexts.find((context) => context.id === this.contextId);
    },
    activeCharacter(): Character | undefined {
      if (this.activeContext?.kind !== "pc") {
        return undefined;
      }

      return this.campaign?.characters.find(
        (character) => character.id === this.activeContext?.character_id,
      );
    },
    contextLabel(): string {
      if (!this.activeContext) {
        return "";
      }

      if (this.activeContext.kind === "gm") {
        return `${this.activeContext.campaign_name} · Game Master`;
      }

      return `${this.activeContext.campaign_name} · ${this.activeContext.character_name}`;
    },
    accountMenuItems(): MenuItem[] {
      const colourModes: Array<{
        label: string;
        value: ThemePreferences["colourMode"];
      }> = [
        { label: "System", value: "system" },
        { label: "Light", value: "light" },
        { label: "Dark", value: "dark" },
      ];
      const palettes: Array<{
        label: string;
        value: ThemePreferences["palette"];
      }> = [
        { label: "Normal", value: "normal" },
        { label: "Red-green colourblind friendly", value: "colourblind" },
      ];

      return [
        {
          label: "Campaign and character",
          icon: "mdi mdi-account-switch-outline",
          items: this.availableContexts.map((context) => ({
            label:
              context.kind === "gm"
                ? `${context.campaign_name} · Game Master`
                : `${context.campaign_name} · ${context.character_name}`,
            icon:
              context.id === this.contextId
                ? "mdi mdi-check"
                : context.kind === "gm"
                  ? "mdi mdi-shield-account-outline"
                  : "mdi mdi-account-outline",
            command: () => void this.selectContext(context),
          })),
        },
        { separator: true },
        {
          label: "Appearance",
          icon: "mdi mdi-palette-outline",
          items: [
            {
              label: "Colour mode",
              icon: "mdi mdi-theme-light-dark",
              items: colourModes.map((option) => ({
                label: option.label,
                icon:
                  option.value === this.colourMode
                    ? "mdi mdi-check"
                    : "mdi mdi-circle-outline",
                command: () => this.setColourMode(option.value),
              })),
            },
            {
              label: "Colour palette",
              icon: "mdi mdi-format-color-fill",
              items: palettes.map((option) => ({
                label: option.label,
                icon:
                  option.value === this.palette
                    ? "mdi mdi-check"
                    : "mdi mdi-circle-outline",
                command: () => this.setPalette(option.value),
              })),
            },
          ],
        },
        { separator: true },
        {
          label: this.busy ? "Signing out…" : "Sign out",
          icon: "mdi mdi-logout",
          disabled: this.busy,
          command: () => void this.signOut(),
        },
      ];
    },
  },
  watch: {
    "$route.fullPath"(): void {
      this.navigationOpen = false;

      if (this.activeContext) {
        rememberContext(this.activeContext);
      }
    },
    activeContext: {
      immediate: true,
      handler(context: ActingContext | undefined): void {
        this.handleContextChange(context);
      },
    },
  },
  mounted(): void {
    this.presenceSweepTimer = window.setInterval(this.expireStalePresence, 10_000);
    void this.loadContexts();
  },
  beforeUnmount(): void {
    this.unsubscribeCampaignChanges?.();
    this.unsubscribeCampaignReconnect?.();
    this.unsubscribeCampaignPresence?.();
    if (this.presenceSweepTimer !== undefined) {
      window.clearInterval(this.presenceSweepTimer);
    }
    disconnectCampaignRealtime();
  },
  methods: {
    contextPath,
    formatCampaignDate,
    toggleAccountMenu(event: Event): void {
      const menu = this.$refs.accountMenu as { toggle: (event: Event) => void };

      menu.toggle(event);
    },
    setColourMode(colourMode: ThemePreferences["colourMode"]): void {
      this.colourMode = colourMode;
      this.applyAppearance();
    },
    setPalette(palette: ThemePreferences["palette"]): void {
      this.palette = palette;
      this.applyAppearance();
    },
    applyAppearance(): void {
      applyThemePreferences({
        colourMode: this.colourMode,
        palette: this.palette,
      });
    },
    async loadContexts(): Promise<void> {
      try {
        this.availableContexts = await contexts();
      } catch {
        this.availableContexts = [];
      }
    },
    async selectContext(context: ActingContext): Promise<void> {
      rememberContext(context);
      await this.$router.push(contextPath(context));
    },
    async signOut(): Promise<void> {
      this.busy = true;

      try {
        await logout();
        disconnectCampaignRealtime();
        await this.$router.push("/login");
      } finally {
        this.busy = false;
      }
    },
    async refreshCampaignChrome(context: ActingContext): Promise<void> {
      try {
        const campaign = await getCampaign(context.id);

        this.campaign = campaign;
        this.members = campaign.members;
        this.incompleteLevelUps = campaign.incomplete_level_ups.map(
          (levelUp) => levelUp.character_name,
        );
      } catch {
        this.campaign = undefined;
        this.members = [];
        this.incompleteLevelUps = [];
      }
    },
    expireStalePresence(): void {
      const cutoff = Date.now() - 60_000;
      this.members = this.members.map((member) => ({
        ...member,
        connected:
          member.connected &&
          member.last_seen_at !== null &&
          Date.parse(member.last_seen_at) >= cutoff,
      }));
    },
    handleContextChange(context: ActingContext | undefined): void {
      this.unsubscribeCampaignChanges?.();
      this.unsubscribeCampaignReconnect?.();
      this.unsubscribeCampaignPresence?.();
      this.campaign = undefined;
      this.members = [];
      this.incompleteLevelUps = [];

      if (!context) {
        disconnectCampaignRealtime();
        return;
      }

      connectCampaignRealtime(context.id);
      void this.refreshCampaignChrome(context);

      this.unsubscribeCampaignChanges = subscribeCampaignChanges(() => {
        void this.refreshCampaignChrome(context);
        campaignRefreshRevision.value += 1;
      });
      this.unsubscribeCampaignReconnect = subscribeCampaignReconnect(() => {
        void this.refreshCampaignChrome(context);
        campaignRefreshRevision.value += 1;
      });
      this.unsubscribeCampaignPresence = subscribeCampaignPresence((event) => {
        this.members = this.members.map((member) =>
          member.id === event.context_id
            ? {
                ...member,
                connected: event.connected,
                last_seen_at: event.last_seen_at,
              }
            : member,
        );
      });
    },
  },
});
</script>
