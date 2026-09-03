import type { Coins } from "@/types"

// D&D 5e coin exchange, all expressed in copper for exact arithmetic.
// 1 gp = 2 ep = 10 sp = 100 cp ; 1 pp = 10 gp
export const COIN_IN_CP: Record<keyof Coins, number> = {
  pp: 1000,
  gp: 100,
  ep: 50,
  sp: 10,
  cp: 1,
}

export const COIN_ORDER: (keyof Coins)[] = ["pp", "gp", "ep", "sp", "cp"]

export const COIN_LABEL: Record<keyof Coins, string> = {
  pp: "Platinum",
  gp: "Gold",
  ep: "Electrum",
  sp: "Silver",
  cp: "Copper",
}

export const COIN_COLOR: Record<keyof Coins, string> = {
  pp: "#cbd5e1",
  gp: "#fbbf24",
  ep: "#a3b18a",
  sp: "#e2e8f0",
  cp: "#d08b5b",
}

export function emptyCoins(): Coins {
  return { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 }
}

/** Total value of a coin purse expressed as a decimal number of gold pieces. */
export function coinsToGold(coins: Coins): number {
  const cp = COIN_ORDER.reduce((sum, k) => sum + coins[k] * COIN_IN_CP[k], 0)
  return cp / 100
}

/** Total raw copper value — useful for exact comparisons. */
export function coinsToCopper(coins: Partial<Coins>): number {
  return COIN_ORDER.reduce((sum, k) => sum + (coins[k] ?? 0) * COIN_IN_CP[k], 0)
}

/**
 * Format a decimal gold amount using the Hoard "¤" glyph, e.g. 1234.5 -> "¤1,234.5".
 * Trims trailing zeros but keeps up to 2 decimal places.
 */
export function formatGold(gold: number): string {
  const rounded = Math.round(gold * 100) / 100
  const str = rounded.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
  return `¤${str}`
}

/** Convenience: format a whole coin purse as its ¤ gold-equivalent. */
export function formatCoins(coins: Coins): string {
  return formatGold(coinsToGold(coins))
}

/** Add a (partial) coin delta onto a purse, returning a new purse. */
export function addCoins(base: Coins, delta: Partial<Coins>): Coins {
  return {
    pp: base.pp + (delta.pp ?? 0),
    gp: base.gp + (delta.gp ?? 0),
    ep: base.ep + (delta.ep ?? 0),
    sp: base.sp + (delta.sp ?? 0),
    cp: base.cp + (delta.cp ?? 0),
  }
}
