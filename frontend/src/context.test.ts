import { describe, expect, it } from "vitest";
import { contextPath, type ActingContext } from "./context";

const campaign = { id: 7, name: "Drippy Chin", is_game_master: true };

describe("acting-context routes", () => {
  it("uses canonical GM and character paths without query arguments", () => {
    const gm: ActingContext = { kind: "gm", campaign };
    const character: ActingContext = {
      kind: "character",
      campaign,
      character: {
        id: 12,
        name: "Ama",
        is_player_character: true,
        is_active: true,
        is_archived: false,
        archived_at: null,
        race: "Human",
        class: "Fighter",
        strength: 10,
        dexterity: 10,
        constitution: 10,
        intelligence: 10,
        wisdom: 10,
        charisma: 10,
        experience: 0,
        money: {},
        inventory: [],
      },
    };

    expect(contextPath(gm)).toBe("/c/7/gm");
    expect(contextPath(character)).toBe("/c/7/characters/12");
  });
});
