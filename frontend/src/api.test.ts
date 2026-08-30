import { afterEach, describe, expect, it, vi } from "vitest";
import { campaignRequest, ensureCampaignRealtime } from "./realtime";
import {
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  initialiseCsrf,
  login,
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
});
