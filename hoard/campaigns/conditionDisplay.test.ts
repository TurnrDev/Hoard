import { describe, expect, it } from "vitest";
import { conditionIcon, conditionIcons } from "./conditionDisplay";

describe("condition presentation", () => {
  it("defines icons for every supported condition", () => {
    expect(Object.keys(conditionIcons)).toEqual([
      "blinded",
      "charmed",
      "deafened",
      "exhaustion",
      "frightened",
      "grappled",
      "incapacitated",
      "invisible",
      "paralyzed",
      "petrified",
      "poisoned",
      "prone",
      "restrained",
      "stunned",
      "unconscious",
      "pacify",
    ]);
  });

  it("falls back safely for campaign-specific conditions", () => {
    expect(conditionIcon("unknown")).toBe("mdi-alert-circle-outline");
  });
});
