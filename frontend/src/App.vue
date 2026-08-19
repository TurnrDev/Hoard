<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { logout } from "./api";
import NavigationMenu from "./components/NavigationMenu.vue";
import {
  contextPath,
  contexts,
  rememberContext,
  type ActingContext,
} from "./context";

const route = useRoute();
const router = useRouter();
const drawer = ref(false);
const isDesktop = ref(window.innerWidth >= 960);
const busy = ref(false);
const availableContexts = ref<ActingContext[]>([]);
const campaignId = computed(() => Number(route.params.id));
const activeContext = computed(() => {
  const characterId = Number(route.params.characterId);
  const inCampaign = availableContexts.value.filter(
    (context) => context.campaign.id === campaignId.value,
  );
  if (route.path.endsWith("/gm"))
    return inCampaign.find((context) => context.kind === "gm");
  if (characterId)
    return inCampaign.find(
      (context) =>
        context.kind === "character" && context.character.id === characterId,
    );
  const remembered = localStorage.getItem(`hoard:context:${campaignId.value}`);
  return inCampaign.find((context) =>
    context.kind === "gm"
      ? remembered === "gm"
      : remembered === `character:${context.character.id}`,
  );
});
const title = computed(() => {
  if (!activeContext.value) return "Hoard";
  return activeContext.value.kind === "gm"
    ? `${activeContext.value.campaign.name} · GM`
    : `${activeContext.value.campaign.name} · ${activeContext.value.character.name}`;
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
  await router.push("/login");
  busy.value = false;
}

function updateViewport(): void {
  isDesktop.value = window.innerWidth >= 960;
  if (isDesktop.value) drawer.value = false;
}

watch(
  () => route.fullPath,
  () => {
    if (activeContext.value) rememberContext(activeContext.value);
  },
);
onMounted(() => {
  window.addEventListener("resize", updateViewport);
  void loadContexts();
});
onBeforeUnmount(() => window.removeEventListener("resize", updateViewport));
</script>

<template>
  <v-app>
    <v-app-bar density="comfortable" class="app-bar">
      <v-app-bar-nav-icon
        v-if="$route.path !== '/login' && !isDesktop"
        aria-label="Open navigation"
        @click="drawer = !drawer"
      />
      <v-app-bar-title class="font-weight-black text-primary"
        >HOARD</v-app-bar-title
      >
      <span v-if="activeContext" class="app-context d-none d-sm-inline">{{
        title
      }}</span>
      <v-menu v-if="$route.path !== '/login'" location="bottom end">
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
                  ? `${context.campaign.name} · GM`
                  : `${context.campaign.name} · ${context.character.name}`
              "
              @click="selectContext(context)"
            />
          </v-list>
          <v-divider />
          <v-card-actions
            ><v-spacer /><v-btn
              :loading="busy"
              prepend-icon="mdi-logout"
              variant="text"
              @click="signOut"
              >Sign out</v-btn
            ></v-card-actions
          >
        </v-card>
      </v-menu>
    </v-app-bar>
    <v-navigation-drawer
      v-if="$route.path !== '/login' && isDesktop"
      permanent
      rail
      expand-on-hover
      width="280"
      rail-width="64"
      class="app-drawer"
    >
      <NavigationMenu
        :campaign-id="campaignId"
        :active-context="activeContext"
      />
    </v-navigation-drawer>
    <v-navigation-drawer
      v-if="$route.path !== '/login' && !isDesktop"
      v-model="drawer"
      temporary
      width="360"
      class="app-drawer mobile-drawer"
    >
      <NavigationMenu
        :campaign-id="campaignId"
        :active-context="activeContext"
      />
    </v-navigation-drawer>
    <v-main><router-view @contexts-changed="loadContexts" /></v-main>
  </v-app>
</template>
