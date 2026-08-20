import { describe, expect, it } from "vitest";
import { formatCampaignDate, ordinal } from "./calendar";

describe("campaign calendar", () => {
  it("formats the requested campaign date", () => {
    expect(
      formatCampaignDate({
        era_abbreviation: "PD",
        era_name: "Powder Dynasty",
        year: 81,
        day: 137,
      }),
    ).toBe("PD81, 137th");
  });

  it("uses correct ordinal suffixes", () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21].map(ordinal)).toEqual([
      "1st",
      "2nd",
      "3rd",
      "4th",
      "11th",
      "12th",
      "13th",
      "21st",
    ]);
  });
});
