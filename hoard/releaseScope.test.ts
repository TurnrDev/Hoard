import { describe, expect, it } from "vitest";
import packageLock from "../package-lock.json?raw";
import packageMetadata from "../package.json?raw";
import pythonMetadata from "../pyproject.toml?raw";
import navigation from "./campaigns/components/CampaignNavigation.vue?raw";
import profile from "./campaigns/pages/CharacterProfileView.vue?raw";
import router from "./router.ts?raw";

describe("initial release UI scope", () => {
  it("keeps Python and frontend release metadata at the same version", () => {
    const pythonVersion = pythonMetadata.match(/^version = "([^"]+)"$/m)?.[1];
    const frontendVersion = JSON.parse(packageMetadata).version;
    const lockVersion = JSON.parse(packageLock).version;

    expect(pythonVersion).toBe("0.1.0");
    expect(frontendVersion).toBe(pythonVersion);
    expect(lockVersion).toBe(pythonVersion);
  });

  it("keeps deferred profile capabilities visible and blocked", () => {
    expect(profile).toContain("<Message");
    expect(profile).toContain("<BlockUI");
    expect(profile).toContain(':blocked="true"');
    expect(profile).toContain("<Skeleton");
    expect(profile).toContain("detailed character sheet");
    expect(profile).toContain("health, abilities, equipment, spells");
    expect(profile).toContain("rests, combat, and level-up");
  });

  it("uses the profile action menu without a character-type editor", () => {
    expect(profile).toContain('label="Character actions"');
    expect(profile).toContain(':items="characterActionItems"');
    expect(profile).not.toContain("Character type</span>");
    expect(profile).not.toContain('v-model="draft.kind"');
  });

  it("keeps Compendium as a disabled coming-soon navigation item", () => {
    expect(navigation).toContain("Compendium");
    expect(navigation).toContain('aria-disabled="true"');
    expect(navigation).toContain("Coming soon");
    expect(router).not.toContain("CompendiumView");
    expect(router).not.toMatch(/\/c\/:id\/compendium/);
  });

  it("does not expose builder or level-up routes", () => {
    expect(router).not.toContain("CharacterBuilderView");
    expect(router).not.toContain("CharacterLevelUpView");
    expect(router).not.toMatch(/characters\/:characterId\/(build|level-up)/);
  });
});
