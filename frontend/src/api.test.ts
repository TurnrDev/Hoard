import { afterEach, describe, expect, it, vi } from "vitest";
import { campaignRequest, ensureCampaignRealtime } from "./realtime";
import {
  addCharacterToEncounter,
  addEncounterCombatant,
  changeCharacterSheetRecord,
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  endEncounter,
  initialiseCsrf,
  login,
  removeCharacterCondition,
  removeEncounterCombatant,
  reorderEncounterCombatants,
  setCurrentEncounterCombatant,
  setCharacterCondition,
  setCombatantCondition,
  startEncounter,
  updateEncounterCombatant,
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

  it("sends inventory moves over the acting context socket", async () => {
    await createInventoryTransaction(8, {
      from_character_id: 2,
      to_character_id: null,
      item_id: 3,
      quantity: 1,
    });

    expect(ensureCampaignRealtime).toHaveBeenCalledWith(8);
    expect(campaignRequest).toHaveBeenCalledWith("inventory.transactions.create", {
      from_character_id: 2,
      to_character_id: null,
      item_id: 3,
      quantity: 1,
    });
  });

  it("sends money transfers and exchanges over the context socket", async () => {
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

  it("creates, updates, and removes character notes over the context socket", async () => {
    await changeCharacterSheetRecord(8, 2, "notes", "create", {
      title: "Plans",
      body: "Visit the old mill.",
    });
    await changeCharacterSheetRecord(
      8,
      2,
      "notes",
      "update",
      {
        title: "New plans",
        body: "Avoid the old mill.",
      },
      17,
    );
    await changeCharacterSheetRecord(8, 2, "notes", "delete", {}, 17);

    expect(campaignRequest).toHaveBeenNthCalledWith(1, "characters.notes.create", {
      character_id: 2,
      fields: {
        title: "Plans",
        body: "Visit the old mill.",
      },
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(2, "characters.notes.update", {
      character_id: 2,
      fields: {
        title: "New plans",
        body: "Avoid the old mill.",
      },
      record_id: 17,
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(3, "characters.notes.delete", {
      character_id: 2,
      fields: {},
      record_id: 17,
    });
  });

  it("sends condition and combatant changes over the context socket", async () => {
    await setCharacterCondition(8, 2, {
      identifier: "exhaustion",
      exhaustion_level: 2,
      source: "Hunger",
      duration: "Until properly fed",
    });
    await removeCharacterCondition(8, 2, 17);
    await setCombatantCondition(8, 31, {
      identifier: "prone",
      source: "Trip attack",
      duration: "Until the combatant stands",
    });
    await updateEncounterCombatant(8, 31, {
      show_hp_bar: true,
      show_hp_numbers: false,
    });

    expect(campaignRequest).toHaveBeenNthCalledWith(1, "characters.conditions.set", {
      character_id: 2,
      identifier: "exhaustion",
      exhaustion_level: 2,
      source: "Hunger",
      duration: "Until properly fed",
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(2, "characters.conditions.remove", {
      character_id: 2,
      condition_id: 17,
    });
    expect(campaignRequest).toHaveBeenNthCalledWith(
      3,
      "campaign.encounter.conditions.set",
      {
        combatant_id: 31,
        identifier: "prone",
        source: "Trip attack",
        duration: "Until the combatant stands",
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      4,
      "campaign.encounter.combatants.update",
      {
        combatant_id: 31,
        show_hp_bar: true,
        show_hp_numbers: false,
      },
    );
  });

  it("manages the encounter lifecycle over the context socket", async () => {
    await startEncounter(8);
    await addCharacterToEncounter(8, 2, 18, {
      show_hp_bar: true,
      show_hp_numbers: false,
    });
    await addEncounterCombatant(8, {
      name: "Goblin 2",
      creature_entry_id: 44,
      initiative: 12,
      current_hp: 7,
      max_hp: 7,
      show_hp_bar: true,
      show_hp_numbers: false,
    });
    await reorderEncounterCombatants(8, [31, 30]);
    await setCurrentEncounterCombatant(8, 30);
    await removeEncounterCombatant(8, 31);
    await endEncounter(8);

    expect(campaignRequest).toHaveBeenNthCalledWith(1, "campaign.encounter.start", {});
    expect(campaignRequest).toHaveBeenNthCalledWith(
      2,
      "campaign.encounter.combatants.add_character",
      {
        character_id: 2,
        initiative: 18,
        show_hp_bar: true,
        show_hp_numbers: false,
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      3,
      "campaign.encounter.combatants.add",
      {
        name: "Goblin 2",
        creature_entry_id: 44,
        initiative: 12,
        current_hp: 7,
        max_hp: 7,
        show_hp_bar: true,
        show_hp_numbers: false,
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      4,
      "campaign.encounter.combatants.reorder",
      {
        combatant_ids: [31, 30],
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      5,
      "campaign.encounter.current.set",
      {
        combatant_id: 30,
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(
      6,
      "campaign.encounter.combatants.remove",
      {
        combatant_id: 31,
      },
    );
    expect(campaignRequest).toHaveBeenNthCalledWith(7, "campaign.encounter.end", {});
  });
});
