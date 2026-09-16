import { afterEach, describe, expect, it, vi } from "vitest";
import { campaignRequest, ensureCampaignRealtime } from "./realtime";
import {
  addCharacterToEncounter,
  addEncounterCombatant,
  chooseInitiativeTie,
  createMoneyExchange,
  createMoneyTransfer,
  createSharedXpAward,
  endEncounter,
  endPlayerTurn,
  initialiseCsrf,
  login,
  removeEncounterCombatant,
  reorderEncounterCombatants,
  reverseTransaction,
  rollPlayerInitiative,
  setCurrentEncounterCombatant,
  startEncounter,
  updateCharacter,
  type LedgerTransaction,
} from "./api";

const { httpRequest } = vi.hoisted(() => ({ httpRequest: vi.fn() }));

vi.mock("axios", () => ({
  default: {
    create: () => ({ request: httpRequest }),
    isAxiosError: () => false,
  },
}));

vi.mock("./realtime", () => ({
  campaignRequest: vi.fn().mockResolvedValue({ id: 4, ledger: "test" }),
  ensureCampaignRealtime: vi.fn().mockResolvedValue(undefined),
  inviteRequest: vi.fn(),
  userRequest: vi.fn(),
}));

describe("API client", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("uses the CSRF token when posting login credentials", async () => {
    httpRequest
      .mockResolvedValueOnce({ status: 200, data: { csrfToken: "token" } })
      .mockResolvedValueOnce({ status: 200, data: { id: 1, username: "jay" } });

    await initialiseCsrf();
    await login("jay", "secret");

    expect(httpRequest).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        url: "/api/auth/session/",
        method: "POST",
        headers: expect.objectContaining({ "X-CSRFToken": "token" }),
      }),
    );
  });

  it("sends money transfers and exchanges over the acting context socket", async () => {
    await createMoneyTransfer(8, {
      from_character_id: 2,
      to_character_id: null,
      amounts: { gp: 3, sp: 4, cp: 7 },
    });
    await createMoneyExchange(8, {
      character_id: 2,
      given: { gp: 1 },
      received: { sp: 10 },
    });

    expect(ensureCampaignRealtime).toHaveBeenCalledWith(8);
    expect(campaignRequest).toHaveBeenNthCalledWith(1, "money.transfers.create", {
      from_character_id: 2,
      to_character_id: null,
      amounts: { gp: 3, sp: 4, cp: 7 },
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(2, "money.exchanges.create", {
      character_id: 2,
      given: { gp: 1 },
      received: { sp: 10 },
    });
  });

  it("sends shared XP awards and ledger reversals over the socket", async () => {
    await createSharedXpAward(8, {
      amount: 250,
      description: "Milestone",
    });
    await reverseTransaction(8, {
      id: 41,
      ledger: "experience",
    } as LedgerTransaction);

    expect(campaignRequest).toHaveBeenNthCalledWith(
      1,
      "experience.shared_awards.create",
      {
        amount: 250,
        description: "Milestone",
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(2, "transactions.reverse", {
      ledger: "experience",
      transaction_id: 41,
    });
  });

  it("maps the display class field to the character command payload", async () => {
    await updateCharacter(8, 2, {
      name: "Wren",
      class: "Wizard",
    });

    expect(campaignRequest).toHaveBeenCalledWith("characters.update", {
      character_id: 2,
      fields: {
        name: "Wren",
        character_class: "Wizard",
      },
    });
  });

  it("manages encounters through the historical socket commands", async () => {
    await startEncounter(8);
    await addCharacterToEncounter(8, 2, 18);
    await addEncounterCombatant(8, {
      name: "Goblin 2",
      initiative: 12,
      current_hp: 7,
      max_hp: 7,
    });
    await reorderEncounterCombatants(8, [31, 30]);
    await setCurrentEncounterCombatant(8, 30);
    await removeEncounterCombatant(8, 31);
    await endEncounter(8);

    expect(campaignRequest).toHaveBeenNthCalledWith(1, "campaign.encounter.start", {});
    expect(campaignRequest).toHaveBeenNthCalledWith(
      2,
      "campaign.encounter.combatants.add_character",
      { character_id: 2, initiative: 18 },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      3,
      "campaign.encounter.combatants.add",
      {
        name: "Goblin 2",
        initiative: 12,
        current_hp: 7,
        max_hp: 7,
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      4,
      "campaign.encounter.combatants.reorder",
      { combatant_ids: [31, 30] },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      5,
      "campaign.encounter.current.set",
      { combatant_id: 30 },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      6,
      "campaign.encounter.combatants.remove",
      { combatant_id: 31 },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(7, "campaign.encounter.end", {});
  });

  it("sends player initiative and turn commands", async () => {
    await rollPlayerInitiative(8, 17);
    await chooseInitiativeTie(8, 31);
    await endPlayerTurn(8);

    expect(campaignRequest).toHaveBeenNthCalledWith(
      1,
      "campaign.encounter.initiative.roll",
      { roll: 17 },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      2,
      "campaign.encounter.initiative.tie.choose",
      { combatant_id: 31 },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      3,
      "campaign.encounter.turn.end",
      {},
    );
  });
});
