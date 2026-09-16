<template>
  <Toast :position="toastPosition" />

  <div
    v-if="showReconnectingScreen"
    class="connection-screen position-fixed d-flex flex-column align-items-center justify-content-center gap-3 p-4 text-center bg-body"
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <ProgressSpinner
      class="connection-screen__spinner"
      aria-label="Reconnecting to Hoard"
      stroke-width="5"
    />
    <div>
      <h1 class="h3 mb-2">Reconnecting…</h1>
      <p class="text-body-secondary mb-0">
        Your session and current page are being kept safe. Hoard will resume
        automatically when the connection returns.
      </p>
    </div>
  </div>

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

    <header class="campaign-header border-bottom bg-body-tertiary">
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
          <span class="campaign-header__version">v{{ version }}</span>
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
      class="bg-body-tertiary"
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
      :class="{
        'campaign-layout--contextless': !activeContext,
        'campaign-layout--rail-expanded': partyRailExpanded,
      }"
    >
      <aside
        v-if="activeContext"
        class="campaign-navigation-panel d-none d-lg-block border-end bg-body-tertiary p-3"
      >
        <CampaignNavigation
          :context-id="contextId"
          :active-context="activeContext"
        />
      </aside>

      <section
        v-if="campaign && activeContext"
        class="campaign-rail-panel border-start bg-body-tertiary"
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
        class="campaign-main container-fluid bg-body py-4 py-lg-5"
      >
        <router-view @contexts-changed="loadContexts" />
      </main>
    </div>
  </div>
</template>

<script lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import type { MenuItem } from "primevue/menuitem";
import ProgressSpinner from "primevue/progressspinner";
import TieredMenu from "primevue/tieredmenu";
import Toast from "primevue/toast";
import { defineComponent } from "vue";
import {
  getSession,
  isUnauthenticatedError,
  logout,
  type Campaign,
  type CampaignMember,
  type Character,
} from "./api";
import { formatCampaignDate } from "@/campaigns/calendar";
import {
  markConnectionAvailable,
  markConnectionUnavailable,
  serverIsReconnecting,
} from "./connection";
import CampaignNavigation from "@/campaigns/components/CampaignNavigation.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import PartyRail from "@/campaigns/components/PartyRail.vue";
import {
  contextPath,
  contexts,
  rememberContext,
  type ActingContext,
} from "@/campaigns/context";
import {
  campaignRefreshRevision,
  connectCampaignRealtime,
  disconnectCampaignRealtime,
  subscribeCampaignCalendar,
  subscribeDomainEvents,
  subscribeCampaignPresence,
  subscribeCampaignReconnect,
} from "./realtime";
import { useCampaignStore } from "@/campaigns/stores/campaign";
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
    PartyRail,
    ProgressSpinner,
    Button,
    TieredMenu,
    Toast,
  },
  data() {
    const themePreferences = readThemePreferences();

    return {
      version: __HOARD_VERSION__,
      navigationOpen: false,
      partyRailExpanded: false,
      busy: false,
      colourMode: themePreferences.colourMode,
      palette: themePreferences.palette,
      availableContexts: [] as ActingContext[],
      campaignStore: useCampaignStore(),
      members: [] as CampaignMember[],
      unsubscribeCampaignChanges: undefined as (() => void) | undefined,
      unsubscribeCampaignCalendar: undefined as (() => void) | undefined,
      unsubscribeCampaignReconnect: undefined as (() => void) | undefined,
      unsubscribeCampaignPresence: undefined as (() => void) | undefined,
      presenceSweepTimer: undefined as number | undefined,
      reconnectTimer: undefined as number | undefined,
      releaseCheckTimer: undefined as number | undefined,
      releasePrompted: false,
      reconnectCheckBusy: false,
      phoneViewport: false,
    };
  },
  computed: {
    campaign(): Campaign | undefined {
      return this.campaignStore.campaign;
    },
    contextId(): number {
      return Number(this.$route.params.id);
    },
    toastPosition(): "bottom-center" | "bottom-right" {
      return this.phoneViewport ? "bottom-center" : "bottom-right";
    },
    isPublicRoute(): boolean {
      return this.$route.path === "/login" || this.$route.path.startsWith("/invites/");
    },
    showReconnectingScreen(): boolean {
      return !this.isPublicRoute && serverIsReconnecting.value;
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
        { label: "Parchment (Light)", value: "light" },
        { label: "Midnight (Dark)", value: "dark" },
      ];
      const palettes: Array<{
        label: string;
        value: ThemePreferences["palette"];
      }> = [
        { label: "Hoard", value: "normal" },
        { label: "Melly", value: "colourblind" },
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
    this.updateViewportMode();
    window.addEventListener("resize", this.updateViewportMode);
    window.addEventListener("offline", this.handleBrowserOffline);
    window.addEventListener("online", this.handleBrowserOnline);
    this.presenceSweepTimer = window.setInterval(this.expireStalePresence, 10_000);
    this.reconnectTimer = window.setInterval(this.checkReconnection, 2_000);
    this.releaseCheckTimer = window.setInterval(this.checkReleaseVersion, 60_000);
    void this.checkReleaseVersion();
    void this.loadContexts();
  },
  beforeUnmount(): void {
    window.removeEventListener("resize", this.updateViewportMode);
    window.removeEventListener("offline", this.handleBrowserOffline);
    window.removeEventListener("online", this.handleBrowserOnline);
    this.unsubscribeCampaignChanges?.();
    this.unsubscribeCampaignCalendar?.();
    this.unsubscribeCampaignReconnect?.();
    this.unsubscribeCampaignPresence?.();
    if (this.presenceSweepTimer !== undefined) {
      window.clearInterval(this.presenceSweepTimer);
    }
    if (this.reconnectTimer !== undefined) {
      window.clearInterval(this.reconnectTimer);
    }
    if (this.releaseCheckTimer !== undefined) {
      window.clearInterval(this.releaseCheckTimer);
    }
    disconnectCampaignRealtime();
  },
  methods: {
    contextPath,
    formatCampaignDate,
    updateViewportMode(): void {
      this.phoneViewport = window.matchMedia("(max-width: 767.98px)").matches;
    },
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
        // Preserve the current context while the connection recovers.
      }
    },
    handleBrowserOffline(): void {
      markConnectionUnavailable("browser");
    },
    handleBrowserOnline(): void {
      markConnectionAvailable("browser");
      void this.checkReconnection();
    },
    async checkReconnection(): Promise<void> {
      if (
        this.isPublicRoute ||
        !serverIsReconnecting.value ||
        this.reconnectCheckBusy ||
        !navigator.onLine
      ) {
        return;
      }

      this.reconnectCheckBusy = true;

      try {
        await getSession();
        await this.loadContexts();
      } catch (error) {
        if (isUnauthenticatedError(error)) {
          disconnectCampaignRealtime();
          await this.$router.push("/login");
        }
      } finally {
        this.reconnectCheckBusy = false;
      }
    },
    async checkReleaseVersion(): Promise<void> {
      if (this.releasePrompted) {
        return;
      }

      try {
        const response = await fetch("/release-manifest.json", { cache: "no-store" });

        if (!response.ok) {
          return;
        }

        const manifest = (await response.json()) as { version?: unknown };

        if (typeof manifest.version === "string" && manifest.version !== this.version) {
          this.releasePrompted = true;
          const refresh = window.confirm(
            "A new Hoard release is available. Refresh now to update?",
          );

          if (refresh) {
            window.location.reload();
          }
        }
      } catch {
        // A failed version check should not interrupt the active campaign.
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
        const campaign = await this.campaignStore.load(context.id);
        this.members = campaign.members;
      } catch {
        // Keep the last rendered campaign visible behind the reconnecting screen.
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
      this.unsubscribeCampaignCalendar?.();
      this.unsubscribeCampaignReconnect?.();
      this.unsubscribeCampaignPresence?.();
      this.campaignStore.clear();
      this.members = [];

      if (!context) {
        disconnectCampaignRealtime();
        return;
      }

      connectCampaignRealtime(context.id);
      void this.refreshCampaignChrome(context);

      this.unsubscribeCampaignChanges = subscribeDomainEvents((event) => {
        if (event.type === "campaign.state_changed") {
          void this.refreshCampaignChrome(context);
          campaignRefreshRevision.value += 1;
        }
      });
      this.unsubscribeCampaignCalendar = subscribeCampaignCalendar((calendar) => {
        if (this.campaignStore.campaign) {
          this.campaignStore.campaign.calendar = calendar;
        }

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
