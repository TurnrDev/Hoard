import { describe, expect, it } from "vitest";
import { formatCompactMoneyValue, formatGoldValue, formatMoneyValue } from "./money";

describe("gold value formatting", () => {
  it("always displays two decimal places", () => {
    expect(formatGoldValue("0.1")).toBe("0.10");
    expect(formatGoldValue(12)).toBe("12.00");
    expect(formatGoldValue(1234.5)).toBe("1,234.50");
    expect(formatMoneyValue("250")).toBe("250.00");
  });

  it("keeps two decimal places in compact layouts", () => {
    expect(formatCompactMoneyValue("0.1")).toBe("0.10");
    expect(formatCompactMoneyValue(1234.5)).toBe("1.23K");
  });
});
