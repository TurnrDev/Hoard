import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createInventoryTransaction,
  createMoneyExchange,
  createMoneyTransfer,
  initialiseCsrf,
  login,
} from "./api";

describe("API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the CSRF token when posting login credentials", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrfToken: "token" }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 1, username: "jay" }), {
          status: 200,
        }),
      );
    vi.stubGlobal("fetch", fetch);

    await initialiseCsrf();
    await login("jay", "secret");

    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/auth/session/",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRFToken": "token" }),
      }),
    );
  });

  it("posts an inventory move to its concrete resource", async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 4, ledger: "inventory" }), {
        status: 201,
      }),
    );
    vi.stubGlobal("fetch", fetch);

    await createInventoryTransaction(8, {
      from_character_id: 2,
      to_character_id: null,
      item_id: 3,
      quantity: 1,
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/contexts/8/inventory-transactions/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          from_character_id: 2,
          to_character_id: null,
          item_id: 3,
          quantity: 1,
        }),
      }),
    );
  });

  it("posts money transfers and exchanges to their concrete resources", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: 4, ledger: "money" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetch);

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

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/contexts/8/money-transfers/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          from_character_id: 2,
          to_character_id: null,
          amounts: { gp: 3, sp: 4, cp: 7 },
        }),
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/contexts/8/money-exchanges/",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
