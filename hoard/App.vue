<template>
  <Toast :position="toastPosition" />

  <InitiativeRollDialog
    v-if="pendingInitiativeCombatant"
    :key="pendingInitiativeCombatant.id"
    :context-id="contextId"
    :combatant="pendingInitiativeCombatant"
    :bonus-roll="pendingInitiativeIsBonus"
  />

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
    :class="{
      'campaign-shell--with-context': activeContext,
      'campaign-shell--contextless': !activeContext,
      'campaign-shell--navigation-expanded': navigationExpanded,
      'campaign-shell--party-expanded': partyRailExpanded,
    }"
  >
    <a
      class="visually-hidden-focusable skip-link border bg-body text-body px-3 py-2"
      href="#main-content"
    >
      Skip to main content
    </a>

    <aside
      v-if="activeContext"
      class="campaign-navigation-panel d-none d-lg-flex flex-column border-end bg-body-tertiary"
      :class="{ 'campaign-navigation-panel--expanded': navigationExpanded }"
      aria-label="Campaign sidebar"
    >
      <header class="campaign-navigation-panel__header d-flex align-items-center gap-2">
        <Button
          :icon="navigationExpanded ? 'mdi mdi-menu-open' : 'mdi mdi-menu'"
          text
          rounded
          :aria-label="
            navigationExpanded ? 'Collapse campaign sidebar' : 'Expand campaign sidebar'
          "
          :aria-expanded="navigationExpanded"
          @click="toggleNavigationRail"
        />
        <RouterLink
          v-if="navigationExpanded"
          class="campaign-navigation-panel__wordmark fw-bold text-decoration-none text-nowrap"
          :to="contextPath(activeContext)"
        >
          HOARD
          <span class="campaign-navigation-panel__version">v{{ version }}</span>
        </RouterLink>
      </header>

      <CampaignNavigation
        :context-id="contextId"
        :active-context="activeContext"
        :expanded="navigationExpanded"
      />

      <div class="campaign-navigation-panel__account d-grid gap-1 mt-auto border-top">
        <button
          type="button"
          class="campaign-navigation-panel__account-control"
          aria-label="Switch campaign or character"
          aria-haspopup="menu"
          aria-controls="desktop-context-menu"
          @click="toggleContextMenu"
        >
          <CharacterAvatar
            v-if="activeCharacter"
            :character="activeCharacter"
            size="menu"
          />
          <span
            v-else
            class="mdi mdi-account-switch-outline campaign-navigation-panel__account-icon"
            aria-hidden="true"
          />
          <span
            v-if="navigationExpanded"
            class="text-truncate"
          >
            {{ contextLabel }}
          </span>
        </button>
        <TieredMenu
          id="desktop-context-menu"
          ref="contextMenu"
          :model="contextSwitcherItems"
          popup
        />

        <button
          type="button"
          class="campaign-navigation-panel__account-control"
          aria-label="Choose appearance"
          aria-haspopup="menu"
          aria-controls="desktop-appearance-menu"
          @click="toggleAppearanceMenu"
        >
          <span
            class="mdi mdi-palette-outline campaign-navigation-panel__account-icon"
            aria-hidden="true"
          />
          <span v-if="navigationExpanded">Appearance</span>
        </button>
        <TieredMenu
          id="desktop-appearance-menu"
          ref="appearanceMenu"
          :model="appearanceMenuItems"
          popup
        />

        <button
          type="button"
          class="campaign-navigation-panel__account-control"
          :disabled="busy"
          :aria-label="busy ? 'Signing out' : 'Sign out'"
          @click="signOut"
        >
          <span
            class="mdi mdi-logout campaign-navigation-panel__account-icon"
            aria-hidden="true"
          />
          <span v-if="navigationExpanded">
            {{ busy ? "Signing out…" : "Sign out" }}
          </span>
        </button>
      </div>
    </aside>

    <header class="campaign-header border-bottom bg-body-tertiary">
      <div class="campaign-header__brand d-flex align-items-center gap-2">
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

      <div
        class="campaign-header__account d-flex align-items-center justify-content-end gap-2"
        :class="{ 'd-lg-none': activeContext }"
      >
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
      class="campaign-navigation-drawer bg-body-tertiary"
      position="left"
    >
      <template #header>
        <RouterLink
          v-if="activeContext"
          class="campaign-navigation-drawer__wordmark fw-bold text-decoration-none text-nowrap"
          :to="contextPath(activeContext)"
          @click="navigationOpen = false"
        >
          HOARD
          <span class="campaign-navigation-drawer__version">v{{ version }}</span>
        </RouterLink>
      </template>
      <CampaignNavigation
        v-if="activeContext"
        :context-id="contextId"
        :active-context="activeContext"
      />
    </Drawer>

    <div class="campaign-layout">
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
  type EncounterCombatant,
} from "./api";
import {
  markConnectionAvailable,
  markConnectionUnavailable,
  serverIsReconnecting,
} from "./connection";
import CampaignNavigation from "@/campaigns/components/CampaignNavigation.vue";
import CharacterAvatar from "@/campaigns/components/CharacterAvatar.vue";
import InitiativeRollDialog from "@/campaigns/components/InitiativeRollDialog.vue";
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

const NAVIGATION_RAIL_STORAGE_KEY = "hoard-navigation-rail-expanded";

function readNavigationRailExpanded(): boolean {
  try {
    return window.localStorage.getItem(NAVIGATION_RAIL_STORAGE_KEY) !== "false";
  } catch {
    return true;
  }
}

export default defineComponent({
  components: {
    CampaignNavigation,
    CharacterAvatar,
    InitiativeRollDialog,
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
      navigationExpanded: readNavigationRailExpanded(),
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
    pendingInitiativeCombatant(): EncounterCombatant | undefined {
      if (this.activeContext?.kind !== "pc") {
        return undefined;
      }

      return this.campaign?.encounter?.combatants.find(
        (combatant) =>
          combatant.character_id === this.activeContext?.character_id &&
          combatant.can_roll_initiative,
      );
    },
    pendingInitiativeIsBonus(): boolean {
      if (!this.pendingInitiativeCombatant) {
        return false;
      }

      return Boolean(
        this.campaign?.encounter?.combatants.some(
          (combatant) =>
            combatant.character_id === this.pendingInitiativeCombatant?.character_id &&
            combatant.id !== this.pendingInitiativeCombatant.id &&
            combatant.initiative_roll === 20,
        ),
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
    contextSwitcherItems(): MenuItem[] {
      return this.availableContexts.map((context) => ({
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
      }));
    },
    appearanceMenuItems(): MenuItem[] {
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
      ];
    },
    accountMenuItems(): MenuItem[] {
      return [
        {
          label: "Campaign and character",
          icon: "mdi mdi-account-switch-outline",
          items: this.contextSwitcherItems,
        },
        { separator: true },
        {
          label: "Appearance",
          icon: "mdi mdi-palette-outline",
          items: this.appearanceMenuItems,
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
    updateViewportMode(): void {
      this.phoneViewport = window.matchMedia("(max-width: 767.98px)").matches;
    },
    toggleAccountMenu(event: Event): void {
      const menu = this.$refs.accountMenu as { toggle: (event: Event) => void };

      menu.toggle(event);
    },
    toggleContextMenu(event: Event): void {
      const menu = this.$refs.contextMenu as { toggle: (event: Event) => void };

      menu.toggle(event);
    },
    toggleAppearanceMenu(event: Event): void {
      const menu = this.$refs.appearanceMenu as { toggle: (event: Event) => void };

      menu.toggle(event);
    },
    toggleNavigationRail(): void {
      this.navigationExpanded = !this.navigationExpanded;

      try {
        window.localStorage.setItem(
          NAVIGATION_RAIL_STORAGE_KEY,
          String(this.navigationExpanded),
        );
      } catch {
        // Storage may be unavailable in a privacy-restricted browser.
      }
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
        if (
          event.type === "campaign.state_changed" ||
          event.type === "character.health_changed"
        ) {
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
