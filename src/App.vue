<script setup lang="ts">
import { computed, ref } from "vue"
import { useDisplay } from "vuetify"
import { useRoute, useRouter } from "vue-router"
import PartyRail from "@/components/PartyRail.vue"
import { useCampaign } from "@/stores/campaign"

const { mdAndUp } = useDisplay()
const route = useRoute()
const router = useRouter()
const store = useCampaign()

const drawer = ref(true)

const playerNav = [
  { title: "Play", icon: "mdi-sword-cross", to: "/play" },
  { title: "Spells", icon: "mdi-auto-fix", to: "/spells" },
  { title: "Inventory", icon: "mdi-bag-personal", to: "/inventory" },
  { title: "Features", icon: "mdi-star-four-points", to: "/features" },
]
const gmNav = [
  { title: "Campaign", icon: "mdi-shield-crown", to: "/gm" },
  { title: "Encounter", icon: "mdi-sword", to: "/gm/encounter" },
  { title: "Rewards", icon: "mdi-treasure-chest", to: "/gm/rewards" },
]

const isGm = computed(() => (route.meta.role as string) === "gm")

// mobile bottom nav depends on which side of the app you're in
const mobileNav = computed(() => (isGm.value ? gmNav : playerNav))
const activeMobile = ref("/play")
const currentPath = computed(() => route.path)

function go(to: string) {
  router.push(to)
}
</script>

<template>
  <v-app>
    <!-- Desktop navigation drawer -->
    <v-navigation-drawer
      v-if="mdAndUp"
      v-model="drawer"
      width="280"
      color="surface"
      border="0"
    >
      <div class="brand">
        <div class="brand__mark font-display">H</div>
        <div class="brand__text">
          <div class="brand__name font-display">Hoard</div>
          <div class="brand__sub">{{ store.campaign.name }}</div>
        </div>
      </div>

      <div class="nav-section">
        <div class="micro-label nav-section__label">Player</div>
        <v-list nav density="comfortable">
          <v-list-item
            v-for="item in playerNav"
            :key="item.to"
            :to="item.to"
            :prepend-icon="item.icon"
            :title="item.title"
            rounded="lg"
            color="primary"
          />
        </v-list>
      </div>

      <div class="nav-section">
        <div class="micro-label nav-section__label">Game Master</div>
        <v-list nav density="comfortable">
          <v-list-item
            v-for="item in gmNav"
            :key="item.to"
            :to="item.to"
            :prepend-icon="item.icon"
            :title="item.title"
            rounded="lg"
            color="secondary"
          />
        </v-list>
      </div>

      <!-- Persistent party rail lives in the drawer footer on desktop -->
      <template #append>
        <div class="rail-wrap">
          <div class="micro-label rail-wrap__label">
            <v-icon size="14" icon="mdi-account-group" class="mr-1" />
            Party
          </div>
          <PartyRail orientation="vertical" />
        </div>
      </template>
    </v-navigation-drawer>

    <!-- App bar -->
    <v-app-bar flat color="background" border="b">
      <v-app-bar-nav-icon v-if="mdAndUp" @click="drawer = !drawer" />
      <div v-else class="brand brand--compact">
        <div class="brand__mark brand__mark--sm font-display">H</div>
        <span class="brand__name font-display">Hoard</span>
      </div>

      <v-toolbar-title v-if="mdAndUp" class="app-title">
        <span class="font-display">{{ route.meta.title }}</span>
        <v-chip
          size="x-small"
          :color="isGm ? 'secondary' : 'primary'"
          variant="tonal"
          class="ml-2"
        >
          {{ isGm ? 'GM' : 'Player' }}
        </v-chip>
      </v-toolbar-title>

      <v-spacer />

      <div class="session-chip">
        <v-icon size="16" icon="mdi-calendar-clock" />
        <span class="d-none d-sm-inline">Session {{ store.campaign.sessionNumber }}</span>
      </div>
    </v-app-bar>

    <v-main>
      <div class="page-scroll">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </v-main>

    <!-- Mobile bottom navigation -->
    <v-bottom-navigation
      v-if="!mdAndUp"
      :model-value="currentPath"
      grow
      color="primary"
      bg-color="surface"
      height="64"
    >
      <v-btn
        v-for="item in mobileNav"
        :key="item.to"
        :value="item.to"
        @click="go(item.to)"
      >
        <v-icon :icon="item.icon" />
        <span>{{ item.title }}</span>
      </v-btn>
      <v-btn :value="isGm ? '/play' : '/gm'" @click="go(isGm ? '/play' : '/gm')">
        <v-icon :icon="isGm ? 'mdi-account' : 'mdi-shield-crown'" />
        <span>{{ isGm ? 'Player' : 'GM' }}</span>
      </v-btn>
    </v-bottom-navigation>
  </v-app>
</template>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px 12px;
}
.brand--compact {
  padding: 0 4px;
  gap: 8px;
}
.brand__mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 1.4rem;
  font-weight: 700;
  color: #04201c;
  background: linear-gradient(135deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-secondary)));
}
.brand__mark--sm {
  width: 32px;
  height: 32px;
  font-size: 1.1rem;
}
.brand__name {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1;
}
.brand__sub {
  font-size: 0.72rem;
  opacity: 0.6;
  margin-top: 2px;
}
.nav-section {
  padding: 4px 8px;
}
.nav-section__label {
  padding: 8px 12px 2px;
}
.rail-wrap {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  max-height: 44vh;
  overflow-y: auto;
}
.rail-wrap__label {
  display: flex;
  align-items: center;
  padding: 0 4px 8px;
}
.app-title {
  display: flex;
  align-items: center;
  font-size: 1.15rem;
}
.session-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-right: 8px;
  border-radius: 10px;
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.04);
  opacity: 0.85;
}
.page-scroll {
  height: 100%;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
