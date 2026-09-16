import { defineStore } from "pinia";
import { getCampaign, type Campaign } from "@/api";

export const useCampaignStore = defineStore("campaign", {
  state: () => ({
    campaign: undefined as Campaign | undefined,
    contextId: undefined as number | undefined,
  }),
  actions: {
    async load(contextId: number): Promise<Campaign> {
      const campaign = await getCampaign(contextId);

      this.contextId = contextId;
      this.campaign = campaign;

      return campaign;
    },
    clear(): void {
      this.contextId = undefined;
      this.campaign = undefined;
    },
  },
});
