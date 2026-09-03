import { createRouter, createWebHistory } from "vue-router"

const routes = [
  { path: "/", redirect: "/play" },
  {
    path: "/play",
    name: "play",
    component: () => import("@/views/PlayView.vue"),
    meta: { title: "Play", icon: "mdi-sword-cross", role: "player" },
  },
  {
    path: "/spells",
    name: "spells",
    component: () => import("@/views/SpellsView.vue"),
    meta: { title: "Spells", icon: "mdi-auto-fix", role: "player" },
  },
  {
    path: "/inventory",
    name: "inventory",
    component: () => import("@/views/InventoryView.vue"),
    meta: { title: "Inventory", icon: "mdi-bag-personal", role: "player" },
  },
  {
    path: "/features",
    name: "features",
    component: () => import("@/views/FeaturesView.vue"),
    meta: { title: "Features", icon: "mdi-star-four-points", role: "player" },
  },
  {
    path: "/gm",
    name: "gm",
    component: () => import("@/views/GmCampaignView.vue"),
    meta: { title: "Campaign", icon: "mdi-shield-crown", role: "gm" },
  },
  {
    path: "/gm/encounter",
    name: "encounter",
    component: () => import("@/views/EncounterView.vue"),
    meta: { title: "Encounter", icon: "mdi-sword", role: "gm" },
  },
  {
    path: "/gm/rewards",
    name: "rewards",
    component: () => import("@/views/RewardsView.vue"),
    meta: { title: "Rewards", icon: "mdi-treasure-chest", role: "gm" },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
