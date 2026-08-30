<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getCalendar, getCampaign, logout, type CampaignCalendar } from "./api";
import { formatCampaignDate } from "./calendar";
import NavigationMenu from "./components/NavigationMenu.vue";
import { contextPath, contexts, rememberContext, type ActingContext } from "./context";
import {
  connectCampaignRealtime,
  campaignRefreshRevision,
  disconnectCampaignRealtime,
  subscribeCampaignReconnect,
  subscribeCampaignChanges,
} from "./realtime";

const route = useRoute();
const router = useRouter();
const drawer = ref(false);
const isDesktop = ref(window.innerWidth >= 960);
const busy = ref(false);
const availableContexts = ref<ActingContext[]>([]);
const calendar = ref<CampaignCalendar>();
const incompleteLevelUps = ref<string[]>([]);
let unsubscribeCampaignChanges: (() => void) | undefined;
let unsubscribeCampaignReconnect: (() => void) | undefined;
const contextId = computed(() => Number(route.params.id));
const isPublicRoute = computed(
  () => route.path === "/login" || route.path.startsWith("/invites/"),
);
const activeContext = computed(() =>
  availableContexts.value.find((context) => context.id === contextId.value),
);
const title = computed(() => {
  if (!activeContext.value) {
    return "Hoard";
  }
  return activeContext.value.kind === "gm"
    ? `${activeContext.value.campaign_name} · GM`
    : `${activeContext.value.campaign_name} · ${activeContext.value.character_name}`;
});

async function loadContexts(): Promise<void> {
  try {
    availableContexts.value = await contexts();
  } catch {
    availableContexts.value = [];
  }
}

async function selectContext(context: ActingContext): Promise<void> {
  rememberContext(context);
  drawer.value = false;
  await router.push(contextPath(context));
}

async function signOut(): Promise<void> {
  busy.value = true;
  await logout();
  disconnectCampaignRealtime();
  await router.push("/login");
  busy.value = false;
}

function updateViewport(): void {
  isDesktop.value = window.innerWidth >= 960;
  if (isDesktop.value) {
    drawer.value = false;
  }
}

watch(
  () => route.fullPath,
  () => {
    if (activeContext.value) {
      rememberContext(activeContext.value);
    }
  },
);
watch(
  activeContext,
  (context) => {
    unsubscribeCampaignChanges?.();
    unsubscribeCampaignReconnect?.();
    calendar.value = undefined;
    incompleteLevelUps.value = [];
    if (!context) {
      disconnectCampaignRealtime();
      return;
    }
    const refreshCalendar = async (): Promise<void> => {
      try {
        const [nextCalendar, campaign] = await Promise.all([
          getCalendar(context.id),
          getCampaign(context.id),
        ]);
        calendar.value = nextCalendar;
        incompleteLevelUps.value = campaign.incomplete_level_ups.map(
          (row) => row.character_name,
        );
      } catch {
        calendar.value = undefined;
        incompleteLevelUps.value = [];
      }
    };
    void refreshCalendar();
    connectCampaignRealtime(context.id);
    unsubscribeCampaignChanges = subscribeCampaignChanges(() => {
      void refreshCalendar();
      campaignRefreshRevision.value += 1;
    });
    unsubscribeCampaignReconnect = subscribeCampaignReconnect(() => {
      void refreshCalendar();
      campaignRefreshRevision.value += 1;
    });
  },
  { immediate: true },
);
onMounted(() => {
  window.addEventListener("resize", updateViewport);
  void loadContexts();
});
onBeforeUnmount(() => window.removeEventListener("resize", updateViewport));
onBeforeUnmount(() => {
  unsubscribeCampaignChanges?.();
  unsubscribeCampaignReconnect?.();
  disconnectCampaignRealtime();
});
</script>

<template>
  <v-app>
    <v-app-bar
      density="comfortable"
      class="app-bar"
    >
      <v-app-bar-nav-icon
        v-if="!isPublicRoute && !isDesktop"
        aria-label="Open navigation"
        @click="drawer = !drawer"
      />
      <v-app-bar-title class="font-weight-black text-primary">HOARD</v-app-bar-title>
      <span
        v-if="calendar"
        class="app-context app-date app-date--center"
        :title="calendar.era_name"
      >
        {{ formatCampaignDate(calendar) }}
      </span>
      <v-spacer />
      <span
        v-if="activeContext"
        class="app-context d-none d-sm-inline"
      >
        {{ title }}
      </span>
      <v-menu
        v-if="!isPublicRoute"
        location="bottom end"
      >
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            icon="mdi-account-circle-outline"
            variant="text"
            aria-label="User menu"
          />
        </template>
        <v-card min-width="280">
          <v-card-subtitle class="pt-4">Campaign and character</v-card-subtitle>
          <v-list density="compact">
            <v-list-item
              v-for="context in availableContexts"
              :key="contextPath(context)"
              :active="contextPath(context) === $route.path"
              :prepend-icon="
                context.kind === 'gm'
                  ? 'mdi-shield-crown-outline'
                  : 'mdi-account-circle-outline'
              "
              :title="
                context.kind === 'gm'
                  ? `${context.campaign_name} · GM`
                  : `${context.campaign_name} · ${context.character_name}`
              "
              @click="selectContext(context)"
            />
          </v-list>
          <v-divider />
          <v-card-actions>
            <v-spacer />
            <v-btn
              :loading="busy"
              prepend-icon="mdi-logout"
              variant="text"
              @click="signOut"
            >
              Sign out
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>
    </v-app-bar>
    <v-navigation-drawer
      v-if="!isPublicRoute && isDesktop"
      permanent
      rail
      expand-on-hover
      width="280"
      rail-width="64"
      class="app-drawer"
    >
      <NavigationMenu
        :context-id="contextId"
        :active-context="activeContext"
        :has-incomplete-level-ups="Boolean(incompleteLevelUps.length)"
      />
    </v-navigation-drawer>
    <v-navigation-drawer
      v-if="!isPublicRoute && !isDesktop"
      v-model="drawer"
      temporary
      width="360"
      class="app-drawer mobile-drawer"
    >
      <NavigationMenu
        :context-id="contextId"
        :active-context="activeContext"
        :has-incomplete-level-ups="Boolean(incompleteLevelUps.length)"
      />
    </v-navigation-drawer>
    <v-main>
      <v-alert
        v-if="incompleteLevelUps.length"
        type="error"
        variant="flat"
        prominent
        title="Level-up incomplete"
        class="ma-3"
      >
        {{ incompleteLevelUps.join(", ") }} still need to finish the approved group
        level-up.
      </v-alert>
      <router-view @contexts-changed="loadContexts" />
    </v-main>
  </v-app>
</template>
