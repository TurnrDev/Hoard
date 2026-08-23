import { describe, expect, it } from "vitest";
import {
  costInGold,
  defaultPickerFilters,
  itemMatchesFilters,
  itemSummary,
} from "./itemPicker";
import type { Item } from "./api";

const sword: Item = {
  id: 1,
  name: "Sun Blade",
  description: "A radiant sword.",
  campaign_id: null,
  created_by_id: null,
  created_by_username: null,
  source_system: "5e",
  source_identifier: "sun-blade",
  source_repository: "https://example.test",
  is_imported: true,
  equipment: {
    category: "weapon",
    source_book: "dmg",
    item_type: "longsword",
    cost_amount: "250",
    cost_currency: "gp",
    weight_amount: "3",
    weight_unit: "pounds",
    rarity: "rare",
    is_magic: true,
    requires_attunement: true,
  },
};

describe("item picker filters", () => {
  it("normalises D&D currencies to gold equivalents", () => {
    expect(
      costInGold({
        ...sword,
        equipment: {
          ...sword.equipment,
          cost_amount: "50",
          cost_currency: "sp",
        },
      }),
    ).toBe(5);
  });

  it("searches catalogue facts and applies the rich filters", () => {
    const filters = defaultPickerFilters();
    filters.search = "radiant";
    expect(itemMatchesFilters(sword, filters)).toBe(true);
    filters.search = "";
    filters.category = "armor";
    expect(itemMatchesFilters(sword, filters)).toBe(false);
    filters.category = "weapon";
    filters.magic = "yes";
    filters.attunement = "yes";
    filters.minCost = 200;
    filters.maxWeight = 3;
    expect(itemMatchesFilters(sword, filters)).toBe(true);
  });

  it("excludes unknown numeric facts only when a range is requested", () => {
    const unknownCost = {
      ...sword,
      equipment: { ...sword.equipment, cost_amount: null, cost_currency: null },
    };
    const filters = defaultPickerFilters();
    expect(itemMatchesFilters(unknownCost, filters)).toBe(true);
    filters.maxCost = 10;
    expect(itemMatchesFilters(unknownCost, filters)).toBe(false);
  });

  it("summarises provenance and usable facts", () => {
    expect(itemSummary(sword)).toBe("5e · dmg · rare · 250 GP · 3 pounds");
  });
});
