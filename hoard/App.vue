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

  <InitiativeRollDialog
    v-if="activeContext?.kind === 'pc' && pendingInitiativeCombatant"
    :context-id="activeContext.id"
    :combatant="pendingInitiativeCombatant"
    :bonus-roll="pendingInitiativeIsBonus"
  />

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
          :in-combat="campaign.encounter !== null"
          :combatants="campaign.encounter?.combatants ?? []"
          @toggle="partyRailExpanded = !partyRailExpanded"
        />
      </section>

      <main
        id="main-content"
        class="campaign-main container-fluid bg-body py-4 py-lg-5"
      >
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
import { formatCampaignDate } from "@/campaigns/calendar";
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
import { alertCurrentTurn } from "@/campaigns/turnAlert";

export default defineComponent({
  components: {
    CampaignNavigation,
    CharacterAvatar,
    Drawer,
    InitiativeRollDialog,
    Message,
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
      incompleteLevelUps: [] as string[],
      unsubscribeCampaignChanges: undefined as (() => void) | undefined,
      unsubscribeCampaignReconnect: undefined as (() => void) | undefined,
      unsubscribeCampaignPresence: undefined as (() => void) | undefined,
      presenceSweepTimer: undefined as number | undefined,
      reconnectTimer: undefined as number | undefined,
      inspirationExpiryTimer: undefined as number | undefined,
      reconnectCheckBusy: false,
      observedCurrentCombatantId: undefined as number | null | undefined,
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
    void this.loadContexts();
  },
  beforeUnmount(): void {
    window.removeEventListener("resize", this.updateViewportMode);
    window.removeEventListener("offline", this.handleBrowserOffline);
    window.removeEventListener("online", this.handleBrowserOnline);
    this.unsubscribeCampaignChanges?.();
    this.unsubscribeCampaignReconnect?.();
    this.unsubscribeCampaignPresence?.();
    if (this.presenceSweepTimer !== undefined) {
      window.clearInterval(this.presenceSweepTimer);
    }
    if (this.reconnectTimer !== undefined) {
      window.clearInterval(this.reconnectTimer);
    }
    if (this.inspirationExpiryTimer !== undefined) {
      window.clearTimeout(this.inspirationExpiryTimer);
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
        const currentCombatantId = campaign.encounter?.current_combatant_id ?? null;
        const shouldAlertCurrentPlayer =
          this.observedCurrentCombatantId !== undefined &&
          currentCombatantId !== null &&
          currentCombatantId !== this.observedCurrentCombatantId &&
          context.kind === "pc" &&
          campaign.encounter?.combatants.some(
            (combatant) =>
              combatant.id === currentCombatantId &&
              combatant.character_id === context.character_id,
          );

        this.scheduleInspirationExpiry(context, campaign);
        this.observedCurrentCombatantId = currentCombatantId;
        this.members = campaign.members;
        this.incompleteLevelUps = campaign.incomplete_level_ups.map(
          (levelUp) => levelUp.character_name,
        );

        if (shouldAlertCurrentPlayer) {
          alertCurrentTurn();
          const currentCombatant = campaign.encounter?.combatants.find(
            (combatant) => combatant.id === currentCombatantId,
          );

          this.$toast.add({
            severity: "info",
            summary: "Your turn",
            detail: currentCombatant
              ? `${currentCombatant.name} is up.`
              : "Your initiative is current.",
            life: 5_000,
          });
        }
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
    scheduleInspirationExpiry(context: ActingContext, campaign: Campaign): void {
      if (this.inspirationExpiryTimer !== undefined) {
        window.clearTimeout(this.inspirationExpiryTimer);
        this.inspirationExpiryTimer = undefined;
      }

      const expiryTimes = campaign.characters
        .filter(
          (character) =>
            character.has_inspiration && character.inspiration_expires_at !== null,
        )
        .map((character) => Date.parse(character.inspiration_expires_at as string))
        .filter((expiry) => Number.isFinite(expiry));

      if (expiryTimes.length === 0) {
        return;
      }

      const nextExpiry = Math.min(...expiryTimes);
      const delay = Math.max(0, nextExpiry - Date.now() + 100);

      this.inspirationExpiryTimer = window.setTimeout(() => {
        void this.refreshCampaignChrome(context);
      }, delay);
    },
    handleContextChange(context: ActingContext | undefined): void {
      this.unsubscribeCampaignChanges?.();
      this.unsubscribeCampaignReconnect?.();
      this.unsubscribeCampaignPresence?.();
      this.campaignStore.clear();
      this.members = [];
      this.incompleteLevelUps = [];
      this.observedCurrentCombatantId = undefined;
      if (this.inspirationExpiryTimer !== undefined) {
        window.clearTimeout(this.inspirationExpiryTimer);
        this.inspirationExpiryTimer = undefined;
      }

      if (!context) {
        disconnectCampaignRealtime();
        return;
      }

      connectCampaignRealtime(context.id);
      void this.refreshCampaignChrome(context);

      this.unsubscribeCampaignChanges = subscribeDomainEvents((event) => {
        if (
          event.type === "character.health_changed" &&
          typeof event.character_id === "number" &&
          typeof event.current_hp === "number" &&
          typeof event.temporary_hp === "number"
        ) {
          this.campaignStore.applyHealthChanged({
            character_id: event.character_id,
            current_hp: event.current_hp,
            temporary_hp: event.temporary_hp,
          });
          return;
        }

        if (event.type === "campaign.state_changed") {
          void this.refreshCampaignChrome(context);
          campaignRefreshRevision.value += 1;
        }
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
