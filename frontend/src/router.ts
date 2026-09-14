import { createRouter, createWebHistory } from "vue-router";
import { getSession, isUnauthenticatedError } from "./api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      component: () => import("./views/LoginView.vue"),
    },
    {
      path: "/invites/:token",
      component: () => import("./views/InviteView.vue"),
    },
    {
      path: "/",
      component: () => import("./views/CampaignListView.vue"),
    },
    {
      path: "/c/:id",
      component: () => import("./views/CampaignRedirectView.vue"),
      props: true,
    },
    {
      path: "/c/:id/gm",
      component: () => import("./views/GmConsoleView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters",
      component: () => import("./views/CharacterDirectoryView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId",
      component: () => import("./views/CharacterProfileView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId/build",
      component: () => import("./views/CharacterBuilderView.vue"),
      props: true,
    },
    {
      path: "/c/:id/characters/:characterId/level-up",
      component: () => import("./views/CharacterLevelUpView.vue"),
      props: true,
    },
    {
      path: "/c/:id/compendium",
      component: () => import("./views/CompendiumView.vue"),
      props: true,
    },
    {
      path: "/c/:id/ledger",
      component: () => import("./views/LedgerView.vue"),
      props: true,
    },
    {
      path: "/c/:id/manage",
      component: () => import("./views/ManageCampaignView.vue"),
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
