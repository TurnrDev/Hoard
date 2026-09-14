export type PartyRailCondition = {
  id: string;
  label: string;
  exhaustionLevel?: number;
};

export type PartyRailCombatant = {
  id: string;
  name: string;
  kind: "pc" | "npc" | "monster";
  initiative: number;
  currentHp: number | null;
  maxHp: number | null;
  conditions: PartyRailCondition[];
  showHpBar: boolean;
  showHpNumbers: boolean;
};
