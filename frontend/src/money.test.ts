import { describe, expect, it } from "vitest";
import { formatGoldValue } from "./money";

describe("gold value formatting", () => {
  it("always displays two decimal places", () => {
    expect(formatGoldValue("0.1")).toBe("0.10");
    expect(formatGoldValue(12)).toBe("12.00");
    expect(formatGoldValue(1234.5)).toBe("1,234.50");
  });
});
