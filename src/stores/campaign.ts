import { defineStore } from "pinia"
import type {
  Character,
  Coins,
  Condition,
  Encounter,
  InventoryEntry,
  Item,
  LedgerEntry,
} from "@/types"
import { CAMPAIGN } from "@/data/campaign"
import { addCoins } from "@/lib/money"
import { levelForXp } from "@/lib/dnd"

// Deep clone the seed so the mock data module stays pristine.
function seed() {
  return JSON.parse(JSON.stringify(CAMPAIGN)) as typeof CAMPAIGN
}

let ledgerCounter = 100

export const useCampaign = defineStore("campaign", {
  state: () => ({
    campaign: seed(),
    selectedCharacterId: "char-thorne" as string,
  }),
  getters: {
    party: (s) => s.campaign.characters,
    selected(s): Character {
      return (
        s.campaign.characters.find((c) => c.id === s.selectedCharacterId) ??
        s.campaign.characters[0]
      )
    },
    activeEncounter: (s): Encounter | undefined =>
      s.campaign.encounters.find((e) => e.active) ?? s.campaign.encounters[0],
    itemMap(s): Record<string, Item> {
      return Object.fromEntries(s.campaign.itemLibrary.map((i) => [i.id, i]))
    },
  },
  actions: {
    selectCharacter(id: string) {
      this.selectedCharacterId = id
    },
    charById(id: string): Character | undefined {
      return this.campaign.characters.find((c) => c.id === id)
    },

    // --- HP ---------------------------------------------------------------
    applyHpDelta(id: string, delta: number) {
      const c = this.charById(id)
      if (!c) return
      if (delta < 0 && c.tempHp > 0) {
        const absorbed = Math.min(c.tempHp, -delta)
        c.tempHp -= absorbed
        delta += absorbed
      }
      c.hp = Math.max(0, Math.min(c.maxHp, c.hp + delta))
      this.syncCombatant(id)
    },
    setTempHp(id: string, value: number) {
      const c = this.charById(id)
      if (!c) return
      c.tempHp = Math.max(0, value)
    },
    toggleCondition(id: string, cond: Condition) {
      const c = this.charById(id)
      if (!c) return
      const i = c.conditions.indexOf(cond)
      if (i >= 0) c.conditions.splice(i, 1)
      else c.conditions.push(cond)
    },

    // --- Death saves ------------------------------------------------------
    setDeathSave(id: string, kind: "successes" | "failures", count: number) {
      const c = this.charById(id)
      if (!c) return
      c.deathSaves[kind] = Math.max(0, Math.min(3, count))
    },
    resetDeathSaves(id: string) {
      const c = this.charById(id)
      if (!c) return
      c.deathSaves.successes = 0
      c.deathSaves.failures = 0
    },
    stabilize(id: string) {
      const c = this.charById(id)
      if (!c) return
      c.deathSaves.successes = 3
      c.deathSaves.failures = 0
    },

    // --- Spell slots ------------------------------------------------------
    useSlot(id: string, level: number) {
      const c = this.charById(id)
      const tier = c?.slots.find((t) => t.level === level)
      if (tier && tier.used < tier.total) tier.used++
    },
    restoreSlot(id: string, level: number) {
      const c = this.charById(id)
      const tier = c?.slots.find((t) => t.level === level)
      if (tier && tier.used > 0) tier.used--
    },
    toggleSpellPrepared(id: string, spellId: string) {
      const c = this.charById(id)
      const sp = c?.spells.find((s) => s.id === spellId)
      if (sp) sp.prepared = !sp.prepared
    },
    longRest(id: string) {
      const c = this.charById(id)
      if (!c) return
      c.hp = c.maxHp
      c.tempHp = 0
      c.slots.forEach((t) => (t.used = 0))
      c.features.forEach((f) => {
        if (f.uses) f.uses.used = 0
      })
      this.syncCombatant(id)
    },

    // --- Features ---------------------------------------------------------
    useFeature(id: string, featureId: string) {
      const c = this.charById(id)
      const f = c?.features.find((x) => x.id === featureId)
      if (f?.uses && f.uses.used < f.uses.total) f.uses.used++
    },
    restoreFeature(id: string, featureId: string) {
      const c = this.charById(id)
      const f = c?.features.find((x) => x.id === featureId)
      if (f?.uses && f.uses.used > 0) f.uses.used--
    },

    // --- Money ------------------------------------------------------------
    setCoins(id: string, coins: Coins) {
      const c = this.charById(id)
      if (c) c.coins = { ...coins }
    },
    adjustCoins(id: string, delta: Partial<Coins>) {
      const c = this.charById(id)
      if (c) c.coins = addCoins(c.coins, delta)
    },

    // --- Inventory --------------------------------------------------------
    addInventory(id: string, entry: InventoryEntry) {
      const c = this.charById(id)
      if (!c) return
      const existing = c.inventory.find((e) => e.itemId === entry.itemId)
      if (existing) existing.qty += entry.qty
      else c.inventory.push({ ...entry })
    },
    removeInventory(id: string, itemId: string) {
      const c = this.charById(id)
      if (!c) return
      c.inventory = c.inventory.filter((e) => e.itemId !== itemId)
    },
    setInventoryQty(id: string, itemId: string, qty: number) {
      const c = this.charById(id)
      const entry = c?.inventory.find((e) => e.itemId === itemId)
      if (!entry) return
      if (qty <= 0) this.removeInventory(id, itemId)
      else entry.qty = qty
    },
    toggleEquipped(id: string, itemId: string) {
      const c = this.charById(id)
      const entry = c?.inventory.find((e) => e.itemId === itemId)
      if (entry) entry.equipped = !entry.equipped
    },
    createLibraryItem(item: Item) {
      if (!this.campaign.itemLibrary.some((i) => i.id === item.id)) {
        this.campaign.itemLibrary.push(item)
      }
    },

    // --- XP ---------------------------------------------------------------
    awardXpToParty(amount: number) {
      this.campaign.characters.forEach((c) => {
        c.xp += amount
        c.level = levelForXp(c.xp)
      })
    },

    // --- Encounter --------------------------------------------------------
    syncCombatant(charId: string) {
      const enc = this.activeEncounter
      const c = this.charById(charId)
      if (!enc || !c) return
      const cb = enc.combatants.find((x) => x.characterId === charId)
      if (cb) {
        cb.hp = c.hp
        cb.maxHp = c.maxHp
        cb.conditions = [...c.conditions]
      }
    },
    combatantHpDelta(combatantId: string, delta: number) {
      const enc = this.activeEncounter
      const cb = enc?.combatants.find((x) => x.id === combatantId)
      if (!cb) return
      cb.hp = Math.max(0, Math.min(cb.maxHp, cb.hp + delta))
      if (cb.characterId) {
        const c = this.charById(cb.characterId)
        if (c) c.hp = cb.hp
      }
    },
    nextTurn() {
      const enc = this.activeEncounter
      if (!enc) return
      enc.activeIndex++
      if (enc.activeIndex >= enc.combatants.length) {
        enc.activeIndex = 0
        enc.round++
      }
    },
    prevTurn() {
      const enc = this.activeEncounter
      if (!enc) return
      enc.activeIndex--
      if (enc.activeIndex < 0) {
        enc.activeIndex = enc.combatants.length - 1
        enc.round = Math.max(1, enc.round - 1)
      }
    },
    sortByInitiative() {
      const enc = this.activeEncounter
      if (!enc) return
      const activeId = enc.combatants[enc.activeIndex]?.id
      enc.combatants.sort((a, b) => b.initiative - a.initiative)
      enc.activeIndex = Math.max(
        0,
        enc.combatants.findIndex((c) => c.id === activeId),
      )
    },
    toggleCombatantCondition(combatantId: string, cond: Condition) {
      const enc = this.activeEncounter
      const cb = enc?.combatants.find((x) => x.id === combatantId)
      if (!cb) return
      const i = cb.conditions.indexOf(cond)
      if (i >= 0) cb.conditions.splice(i, 1)
      else cb.conditions.push(cond)
    },

    // --- Ledger -----------------------------------------------------------
    addLedgerEntry(entry: Omit<LedgerEntry, "id">) {
      this.campaign.ledger.unshift({ id: `led-${ledgerCounter++}`, ...entry })
    },
  },
})
