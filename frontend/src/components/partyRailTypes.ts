export type PartyRailCondition = {
  id: string;
  label: string;
  exhaustionLevel?: number;
  source?: string;
  duration?: string;
  instances?: Array<{
    id: number;
    source: string;
    duration: string;
  }>;
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
