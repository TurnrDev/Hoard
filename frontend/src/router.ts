import { createRouter, createWebHistory } from "vue-router";
import CampaignListView from "./views/CampaignListView.vue";
import CampaignView from "./views/CampaignView.vue";
import CharacterActionsView from "./views/CharacterActionsView.vue";
import GmConsoleView from "./views/GmConsoleView.vue";
import LoginView from "./views/LoginView.vue";
import ManageCampaignView from "./views/ManageCampaignView.vue";
import MyCharactersView from "./views/MyCharactersView.vue";
import { getSession } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    { path: "/", component: CampaignListView },
    { path: "/c/:id", component: CampaignView, props: true },
    { path: "/c/:id/actions", component: CharacterActionsView, props: true },
    { path: "/c/:id/gm", component: GmConsoleView, props: true },
    { path: "/c/:id/manage", component: ManageCampaignView, props: true },
    { path: "/c/:id/characters/me", component: MyCharactersView, props: true },
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
