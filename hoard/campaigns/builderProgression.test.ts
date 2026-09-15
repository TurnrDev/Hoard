import { describe, expect, it } from "vitest";
import { classLevelAt } from "./builderProgression";

describe("class progression", () => {
  it("unlocks a subclass at the matching single-class level", () => {
    const levels = [1, 2, 3].map((level) => ({
      level,
      class_entry_id: 164,
      class_name: "Ranger",
    }));

    expect(classLevelAt(levels, levels[0])).toBe(1);
    expect(classLevelAt(levels, levels[1])).toBe(2);
    expect(classLevelAt(levels, levels[2])).toBe(3);
  });

  it("uses class level rather than campaign level for multiclass unlocks", () => {
    const levels = [
      { level: 1, class_entry_id: 160, class_name: "Fighter" },
      { level: 2, class_entry_id: 169, class_name: "Wizard" },
      { level: 3, class_entry_id: 160, class_name: "Fighter" },
      { level: 4, class_entry_id: 169, class_name: "Wizard" },
    ];

    expect(classLevelAt(levels, levels[2])).toBe(2);
    expect(classLevelAt(levels, levels[3])).toBe(2);
  });
});
