import { describe, expect, it } from "vitest";
import { exchangedCoinAmount } from "./coinExchange";

describe("coin exchange amounts", () => {
  it("converts larger denominations into smaller coins", () => {
    expect(exchangedCoinAmount("gp", "sp", 3)).toBe(30);
  });

  it("converts smaller denominations into larger coins when exact", () => {
    expect(exchangedCoinAmount("sp", "gp", 10)).toBe(1);
  });

  it("rejects lossy, invalid, and same-denomination exchanges", () => {
    expect(exchangedCoinAmount("sp", "gp", 1)).toBeNull();
    expect(exchangedCoinAmount("gp", "gp", 1)).toBeNull();
    expect(exchangedCoinAmount("gp", "sp", 0)).toBeNull();
  });
});
