import type { Item } from "./api";
import { displayCoin } from "./display";

export type PickerCandidate = { item: Item; quantity?: number };
export type PickerFilters = {
  search: string;
  system: string | null;
  sourceBook: string | null;
  category: string | null;
  itemType: string | null;
  rarity: string | null;
  magic: "any" | "yes" | "no";
  attunement: "any" | "yes" | "no";
  minCost: number | null;
  maxCost: number | null;
  minWeight: number | null;
  maxWeight: number | null;
};

const currencyGoldValues: Record<string, number> = {
  cp: 0.01,
  sp: 0.1,
  ep: 0.5,
  gp: 1,
  pp: 10,
};

export const defaultPickerFilters = (): PickerFilters => ({
  search: "",
  system: null,
  sourceBook: null,
  category: null,
  itemType: null,
  rarity: null,
  magic: "any",
  attunement: "any",
  minCost: null,
  maxCost: null,
  minWeight: null,
  maxWeight: null,
});

export function costInGold(item: Item): number | null {
  const amount =
    item.equipment.cost_amount === null ? null : Number(item.equipment.cost_amount);
  const multiplier = item.equipment.cost_currency
    ? currencyGoldValues[item.equipment.cost_currency]
    : undefined;
  return amount === null || !Number.isFinite(amount) || multiplier === undefined
    ? null
    : amount * multiplier;
}

export function itemMatchesFilters(item: Item, filters: PickerFilters): boolean {
  const searchable = [
    item.name,
    item.description,
    item.source_system,
    item.source_repository,
    item.equipment.source_book,
    item.equipment.category,
    item.equipment.item_type,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLocaleLowerCase();
  if (filters.search && !searchable.includes(filters.search.toLocaleLowerCase()))
    return false;
  if (filters.system && item.source_system !== filters.system) return false;
  if (filters.sourceBook && item.equipment.source_book !== filters.sourceBook)
    return false;
  if (filters.category && item.equipment.category !== filters.category) return false;
  if (filters.itemType && item.equipment.item_type !== filters.itemType) return false;
  if (filters.rarity && item.equipment.rarity !== filters.rarity) return false;
  if (filters.magic !== "any" && item.equipment.is_magic !== (filters.magic === "yes"))
    return false;
  if (
    filters.attunement !== "any" &&
    item.equipment.requires_attunement !== (filters.attunement === "yes")
  )
    return false;
  const cost = costInGold(item);
  if (
    (filters.minCost !== null && (cost === null || cost < filters.minCost)) ||
    (filters.maxCost !== null && (cost === null || cost > filters.maxCost))
  )
    return false;
  const weight =
    item.equipment.weight_amount === null ? null : Number(item.equipment.weight_amount);
  if (
    (filters.minWeight !== null && (weight === null || weight < filters.minWeight)) ||
    (filters.maxWeight !== null && (weight === null || weight > filters.maxWeight))
  )
    return false;
  return true;
}

export function itemSummary(item: Item): string {
  const facts = [
    item.source_system
      ? `${item.source_system}${item.equipment.source_book ? ` · ${item.equipment.source_book}` : ""}`
      : "Campaign custom",
    item.equipment.rarity,
    item.equipment.cost_amount && item.equipment.cost_currency
      ? `${item.equipment.cost_amount} ${displayCoin(item.equipment.cost_currency)}`
      : null,
    item.equipment.weight_amount && item.equipment.weight_unit
      ? `${item.equipment.weight_amount} ${item.equipment.weight_unit}`
      : null,
  ];
  return facts.filter((value): value is string => Boolean(value)).join(" · ");
}
