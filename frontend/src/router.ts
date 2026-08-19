import { createRouter, createWebHistory } from "vue-router";
import CampaignListView from "./views/CampaignListView.vue";
import CampaignView from "./views/CampaignView.vue";
import GmConsoleView from "./views/GmConsoleView.vue";
import LoginView from "./views/LoginView.vue";
import { getSession } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    { path: "/campaigns", component: CampaignListView },
    { path: "/campaigns/:id", component: CampaignView, props: true },
    { path: "/campaigns/:id/gm", component: GmConsoleView, props: true },
    { path: "/:pathMatch(.*)*", redirect: "/campaigns" },
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
