import { describe, expect, it } from "vitest";
import { nearLevelUpXpThreshold } from "./experience";

describe("experience progress", () => {
  it("marks the final 20% of a level as near level-up", () => {
    expect(nearLevelUpXpThreshold(5_000)).toBe(1_000);
  });
});
