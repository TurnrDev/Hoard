import { afterEach, describe, expect, it, vi } from "vitest";
import { campaignRequest, ensureCampaignRealtime } from "./realtime";
import {
  createSharedXpAward,
  linkDiceCloudCharacter,
  setCharacterActive,
  unlinkDiceCloudCharacter,
} from "./api";

const { httpRequest } = vi.hoisted(() => ({ httpRequest: vi.fn() }));

vi.mock("axios", () => ({
  default: { create: () => ({ request: httpRequest }), isAxiosError: () => false },
}));

vi.mock("./realtime", () => ({
  campaignRequest: vi.fn().mockResolvedValue(undefined),
  ensureCampaignRealtime: vi.fn().mockResolvedValue(undefined),
  inviteRequest: vi.fn(),
  userRequest: vi.fn(),
}));

describe("API client", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("manages a DiceCloud link through the campaign socket", async () => {
    await linkDiceCloudCharacter(8, 2, "sfdxGdwav3hoNATLJ");
    await setCharacterActive(8, 2, false);
    await unlinkDiceCloudCharacter(8, 2);

    expect(ensureCampaignRealtime).toHaveBeenCalledWith(8);
    expect(campaignRequest).toHaveBeenNthCalledWith(1, "characters.dicecloud.link", {
      character_id: 2,
      creature: "sfdxGdwav3hoNATLJ",
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(2, "characters.active.set", {
      character_id: 2,
      is_active: false,
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(3, "characters.dicecloud.unlink", {
      character_id: 2,
    });
  });

  it("sends party XP awards without individual character data", async () => {
    await createSharedXpAward(8, { amount: 250, description: "Milestone" });

    expect(campaignRequest).toHaveBeenCalledWith("experience.shared_awards.create", {
      amount: 250,
      description: "Milestone",
    });
  });
});
