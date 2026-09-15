import { describe, expect, it } from "vitest";
import { displayCoin, displayIdentifier, formatCoinPouch } from "./display";

describe("display values", () => {
  it("turns internal identifiers into readable labels", () => {
    expect(displayIdentifier("initiative")).toBe("Initiative");
    expect(displayIdentifier("temporary_hp")).toBe("Temporary HP");
  });

  it("formats coin denominations and pouches for display", () => {
    expect(displayCoin("gp")).toBe("GP");
    expect(formatCoinPouch({ gp: 1_234, sp: 5 })).toBe(
      "0 PP · 1,234 GP · 0 EP · 5 SP · 0 CP",
    );
  });
});
