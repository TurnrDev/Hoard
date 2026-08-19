import { describe, expect, it } from "vitest";
import { contextPath } from "./context";

describe("context routes", () => {
  it("uses one opaque context identifier without query arguments", () => {
    expect(
      contextPath({
        id: 12,
        campaign_id: 7,
        campaign_name: "Drippy Chin",
        kind: "pc",
        character_id: 4,
        character_name: "Ama",
      }),
    ).toBe("/c/12");
  });
});
