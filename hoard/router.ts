import { createRouter, createWebHistory } from "vue-router";
import { getSession, isUnauthenticatedError } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      component: () => import("@/pages/LoginView.vue"),
    },
    {
      path: "/invites/:token",
      component: () => import("@/pages/InviteView.vue"),
    },
    {
      path: "/",
      component: () => import("@/campaigns/pages/CampaignListView.vue"),
    },
    {
      path: "/c/:id",
      component: () => import("@/campaigns/pages/CampaignRedirectView.vue"),
      props: true,
    },
    {
      path: "/c/:id/gm",
      component: () => import("@/campaigns/pages/GmConsoleView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters",
      component: () => import("@/campaigns/pages/CharacterDirectoryView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId",
      component: () => import("@/campaigns/pages/CharacterProfileView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId/build",
      component: () => import("@/campaigns/pages/CharacterBuilderView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId/level-up",
      component: () => import("@/campaigns/pages/CharacterLevelUpView.vue"),
      props: true,
    },
    {
      path: "/c/:id/compendium",
      component: () => import("@/compendium/pages/CompendiumView.vue"),
      props: true,
    },
    {
      path: "/c/:id/ledger",
      component: () => import("@/campaigns/pages/LedgerView.vue"),
      props: true,
    },
    {
      path: "/c/:id/manage",
      component: () => import("@/campaigns/pages/ManageCampaignView.vue"),
      props: true,
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  if (to.path === "/login" || to.path.startsWith("/invites/")) {
    return true;
  }
  try {
    await getSession();
    return true;
  } catch (error) {
    if (isUnauthenticatedError(error)) {
      return "/login";
    }

    return true;
  }
});

export default router;
