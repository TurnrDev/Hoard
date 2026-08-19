import { afterEach, describe, expect, it, vi } from "vitest";
import { initialiseCsrf, login } from "./api";

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
      "/api/auth/login/",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRFToken": "token" }),
      }),
    );
  });
});
