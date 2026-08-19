import { afterEach, describe, expect, it, vi } from "vitest";
import { createInventoryTransaction, initialiseCsrf, login } from "./api";

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
});
