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
    applyHealthChanged(event: {
      character_id: number;
      current_hp: number;
      temporary_hp: number;
    }): void {
      if (!this.campaign) {
        return;
      }

      const character = this.campaign.characters.find(
        (candidate) => candidate.id === event.character_id,
      );

      if (character) {
        character.sheet.current_hp = event.current_hp;
        character.sheet.temporary_hp = event.temporary_hp;
      }

      const combatants = this.campaign.encounter?.combatants ?? [];
      for (const combatant of combatants) {
        if (combatant.character_id === event.character_id) {
          combatant.current_hp = event.current_hp;
          combatant.max_hp = combatant.is_player_character
            ? (character?.sheet.max_hp ?? null)
            : 100;
          combatant.health_percentage =
            combatant.max_hp === null || combatant.max_hp === 0
              ? null
              : Math.round((combatant.current_hp * 100) / combatant.max_hp);
        }
      }
    },
  },
});
