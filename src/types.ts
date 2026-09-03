// Domain types for Hoard — D&D 5e campaign & character management.

export type AbilityKey = "str" | "dex" | "con" | "int" | "wis" | "cha"

export interface Abilities {
  str: number
  dex: number
  con: number
  int: number
  wis: number
  cha: number
}

// Coin purse. All values are counts of each denomination.
export interface Coins {
  pp: number // platinum
  gp: number // gold
  ep: number // electrum
  sp: number // silver
  cp: number // copper
}

export type ItemCategory =
  | "weapon"
  | "armor"
  | "consumable"
  | "gear"
  | "treasure"
  | "wondrous"
  | "tool"

export type ItemRarity =
  | "common"
  | "uncommon"
  | "rare"
  | "very rare"
  | "legendary"

export interface Item {
  id: string
  name: string
  category: ItemCategory
  rarity: ItemRarity
  weight: number // lb, per unit
  valueGp: number // market value in gold, per unit
  description: string
  attunement?: boolean
  tags?: string[]
}

export interface InventoryEntry {
  itemId: string
  qty: number
  equipped?: boolean
  attuned?: boolean
}

export type SpellSchool =
  | "abjuration"
  | "conjuration"
  | "divination"
  | "enchantment"
  | "evocation"
  | "illusion"
  | "necromancy"
  | "transmutation"

export interface Spell {
  id: string
  name: string
  level: number // 0 = cantrip
  school: SpellSchool
  castingTime: string
  range: string
  components: string
  duration: string
  concentration?: boolean
  ritual?: boolean
  description: string
  prepared?: boolean
}

export interface SpellSlotTier {
  level: number
  total: number
  used: number
}

export interface Feature {
  id: string
  name: string
  source: string // class, race, feat, background
  description: string
  uses?: { total: number; used: number; per: "short" | "long" | "day" }
}

export type Condition =
  | "blinded"
  | "charmed"
  | "frightened"
  | "grappled"
  | "poisoned"
  | "prone"
  | "restrained"
  | "stunned"
  | "unconscious"
  | "concentrating"

export interface Character {
  id: string
  name: string
  playerName: string
  class: string
  subclass?: string
  level: number
  race: string
  background: string
  alignment: string
  avatarColor: string
  initials: string

  abilities: Abilities
  proficiencyBonus: number
  ac: number
  speed: number
  initiative: number

  hp: number
  maxHp: number
  tempHp: number
  hitDice: string

  spellcaster: boolean
  spellAbility?: AbilityKey
  spellSaveDc?: number
  spellAttack?: number
  slots: SpellSlotTier[]
  spells: Spell[]

  inventory: InventoryEntry[]
  coins: Coins
  features: Feature[]
  conditions: Condition[]

  xp: number
  passivePerception: number
  savingThrows: AbilityKey[]
  skills: string[]
}

export interface EncounterCombatant {
  id: string
  name: string
  kind: "pc" | "npc" | "monster"
  initiative: number
  ac: number
  hp: number
  maxHp: number
  characterId?: string // link to a PC
  conditions: Condition[]
}

export interface Encounter {
  id: string
  name: string
  round: number
  activeIndex: number
  active: boolean
  combatants: EncounterCombatant[]
  xpBudget: number
}

export interface LedgerEntry {
  id: string
  timestamp: string
  type: "xp" | "loot" | "gold" | "note"
  summary: string
  detail?: string
  xpEach?: number
  items?: { name: string; qty: number }[]
  coins?: Partial<Coins>
}

export interface Campaign {
  id: string
  name: string
  gmName: string
  setting: string
  sessionNumber: number
  nextSession: string
  characters: Character[]
  encounters: Encounter[]
  ledger: LedgerEntry[]
  itemLibrary: Item[]
}
