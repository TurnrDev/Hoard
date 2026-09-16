const NEAR_LEVEL_UP_PORTION = 0.2;

export function nearLevelUpXpThreshold(levelXpRequirement: number): number {
  return levelXpRequirement * NEAR_LEVEL_UP_PORTION;
}
