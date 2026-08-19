import {
  getCampaign,
  getCampaigns,
  getMyCharacters,
  type CampaignSummary,
  type Character,
} from "./api";

export type ActingContext =
  | { kind: "gm"; campaign: CampaignSummary }
  | { kind: "character"; campaign: CampaignSummary; character: Character };

const storageKey = (campaignId: number) => `hoard:context:${campaignId}`;

export function contextPath(context: ActingContext): string {
  return context.kind === "gm"
    ? `/c/${context.campaign.id}/gm`
    : `/c/${context.campaign.id}/characters/${context.character.id}`;
}

export function rememberContext(context: ActingContext): void {
  localStorage.setItem(
    storageKey(context.campaign.id),
    context.kind === "gm" ? "gm" : `character:${context.character.id}`,
  );
  localStorage.setItem("hoard:last-campaign", String(context.campaign.id));
}

export async function contexts(): Promise<ActingContext[]> {
  const campaigns = await getCampaigns();
  const groups = await Promise.all(
    campaigns.map(async (campaign) => {
      const ownCharacters = await getMyCharacters(campaign.id);
      return [
        ...(campaign.is_game_master ? [{ kind: "gm" as const, campaign }] : []),
        ...ownCharacters
          .filter((character) => character.is_active && !character.is_archived)
          .map((character) => ({
            kind: "character" as const,
            campaign,
            character,
          })),
      ];
    }),
  );
  return groups.flat();
}

export async function defaultContext(
  campaignId: number,
): Promise<ActingContext | undefined> {
  const available = (await contexts()).filter(
    (context) => context.campaign.id === campaignId,
  );
  const remembered = localStorage.getItem(storageKey(campaignId));
  const found = available.find((context) =>
    context.kind === "gm"
      ? remembered === "gm"
      : remembered === `character:${context.character.id}`,
  );
  return (
    found ?? available.find((context) => context.kind === "gm") ?? available[0]
  );
}

export async function validateCharacterContext(
  campaignId: number,
  characterId: number,
): Promise<Character | undefined> {
  const campaign = await getCampaign(campaignId);
  const ownCharacters = await getMyCharacters(campaignId);
  const character = ownCharacters.find(
    (candidate) =>
      candidate.id === characterId &&
      candidate.is_active &&
      !candidate.is_archived,
  );
  if (!character) return undefined;
  rememberContext({ kind: "character", campaign, character });
  return character;
}
