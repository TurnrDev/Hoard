import type { AbilityKey, Abilities } from "@/types"

// 5e XP thresholds per character level (index 0 unused).
export const XP_FOR_LEVEL = [
  0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000,
  120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
]

export function levelForXp(xp: number): number {
  let level = 1
  for (let l = 1; l < XP_FOR_LEVEL.length; l++) {
    if (xp >= XP_FOR_LEVEL[l]) level = l
  }
  return level
}

export function xpProgress(xp: number): { level: number; into: number; span: number; pct: number } {
  const level = levelForXp(xp)
  const floor = XP_FOR_LEVEL[level] ?? 0
  const next = XP_FOR_LEVEL[level + 1] ?? floor
  const span = Math.max(1, next - floor)
  const into = xp - floor
  return { level, into, span, pct: Math.min(100, Math.round((into / span) * 100)) }
}

/**
 * Distribute a total XP amount across N party members using a floor split.
 * Any remainder is reported separately so the GM can decide what to do with it.
 */
export function splitXp(total: number, members: number): { each: number; remainder: number } {
  if (members <= 0) return { each: 0, remainder: total }
  const each = Math.floor(total / members)
  return { each, remainder: total - each * members }
}

export const ABILITY_NAME: Record<AbilityKey, string> = {
  str: "Strength",
  dex: "Dexterity",
  con: "Constitution",
  int: "Intelligence",
  wis: "Wisdom",
  cha: "Charisma",
}

export const ABILITY_ORDER: AbilityKey[] = ["str", "dex", "con", "int", "wis", "cha"]

export function abilityMod(score: number): number {
  return Math.floor((score - 10) / 2)
}

export function formatMod(mod: number): string {
  return mod >= 0 ? `+${mod}` : `${mod}`
}

export function modFor(abilities: Abilities, key: AbilityKey): number {
  return abilityMod(abilities[key])
}
