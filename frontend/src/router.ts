import { createRouter, createWebHistory } from "vue-router";
import CampaignListView from "./views/CampaignListView.vue";
import CampaignRedirectView from "./views/CampaignRedirectView.vue";
import CharacterDirectoryView from "./views/CharacterDirectoryView.vue";
import CharacterProfileView from "./views/CharacterProfileView.vue";
import CompendiumView from "./views/CompendiumView.vue";
import GmConsoleView from "./views/GmConsoleView.vue";
import LedgerView from "./views/LedgerView.vue";
import LoginView from "./views/LoginView.vue";
import ManageCampaignView from "./views/ManageCampaignView.vue";
import { getSession } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    { path: "/", component: CampaignListView },
    { path: "/c/:id", component: CampaignRedirectView, props: true },
    { path: "/c/:id/gm", component: GmConsoleView, props: true },
    {
      path: "/c/:id/characters",
      component: CharacterDirectoryView,
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId",
      component: CharacterProfileView,
      props: true,
    },
    { path: "/c/:id/compendium", component: CompendiumView, props: true },
    { path: "/c/:id/ledger", component: LedgerView, props: true },
    { path: "/c/:id/manage", component: ManageCampaignView, props: true },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  if (to.path === "/login") return true;
  try {
    await getSession();
    return true;
  } catch {
    return "/login";
  }
});

export default router;
