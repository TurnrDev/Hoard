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

    expect(frontendVersion).toBe(pythonVersion);
    expect(lockVersion).toBe(pythonVersion);
  });

  it("renders DiceCloud data without local sheet controls", () => {
    expect(profile).toContain('label: "DiceCloud"');
    expect(profile).toContain("connectionDialogVisible");
    expect(profile).toContain("View on DiceCloud");
    expect(profile).toContain("linkDiceCloudCharacter");
    expect(profile).not.toContain("postHealth");
    expect(profile).not.toContain("uploadCharacterPortrait");
    expect(profile).not.toContain("createMoneyTransfer");
  });

  it("exposes the party XP ledger and removes Compendium", () => {
    expect(navigation).toContain("Ledger");
    expect(navigation).not.toContain("Compendium");
    expect(router).toContain("LedgerView");
    expect(router).toMatch(/\/c\/:id\/ledger/);
    expect(router).not.toMatch(/\/c\/:id\/compendium/);
  });

  it("does not expose builder or level-up routes", () => {
    expect(router).not.toContain("CharacterBuilderView");
    expect(router).not.toContain("CharacterLevelUpView");
    expect(router).not.toMatch(/characters\/:characterId\/(build|level-up)/);
  });
});
