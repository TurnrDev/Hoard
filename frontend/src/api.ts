import { campaignRequest, ensureCampaignRealtime } from "./realtime";

export type User = { id: number; username: string };
export type CampaignSummary = {
  id: number;
  name: string;
  is_game_master: boolean;
};
export type CampaignContext = {
  id: number;
  campaign_id: number;
  campaign_name: string;
  kind: "gm" | "pc";
  character_id: number | null;
  character_name: string | null;
};
export type CampaignCalendar = {
  era_abbreviation: string;
  era_name: string;
  year: number;
  day: number;
};
export type CampaignMember = {
  id: number;
  username: string;
  is_game_master: boolean;
  is_active: boolean;
};
export type EquipmentMetadata = {
  category: string | null;
  source_book: string | null;
  item_type: string | null;
  cost_amount: string | null;
  cost_currency: string | null;
  weight_amount: string | null;
  weight_unit: string | null;
  rarity: string | null;
  is_magic: boolean | null;
  requires_attunement: boolean | null;
};
export type Item = {
  id: number;
  name: string;
  description: string;
  campaign_id: number | null;
  created_by_id: number | null;
  created_by_username: string | null;
  source_system: string | null;
  source_identifier: string | null;
  source_repository: string | null;
  equipment: EquipmentMetadata;
  is_imported: boolean;
};
export type Character = {
  id: number;
  context_id: number | null;
  name: string;
  is_player_character: boolean;
  is_active: boolean;
  is_archived: boolean;
  archived_at: string | null;
  race: string;
  class: string;
  background: string;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  sheet: {
    level: number;
    base_hp: number;
    max_hp: number;
    current_hp: number;
    temporary_hp: number;
    base_ac: number;
    ac_adjustment: number;
    armor_class: number;
    speed: string;
    spell_slots: Record<string, number>;
    proficiency_bonus_adjustment: number;
    proficiency_bonus: number;
    abilities: Record<string, { score: number; modifier: number; adjustment: number }>;
    saves: Record<string, { proficient: boolean; adjustment: number; bonus: number }>;
    skills: Record<string, { proficiency: string; bonus: number }>;
  };
  experience: number;
  money: Record<string, number | string>;
  inventory: Array<{ item_id: number; name: string; quantity: number }>;
  notes: Array<{ id: number; title: string; body: string }>;
  features: Array<{
    id: number;
    kind: string;
    name: string;
    description: string;
    notes: string;
    catalogue_entry_id: number | null;
  }>;
  spells: Array<{
    id: number;
    name: string;
    level: number;
    description: string;
    notes: string;
    prepared: boolean;
    catalogue_entry_id: number | null;
  }>;
  loadout: Array<{
    id: number;
    item_id: number;
    name: string;
    equipped: boolean;
    label: string;
  }>;
  companions: Array<{
    id: number;
    name: string;
    armor_class: number;
    max_hp: number;
    current_hp: number;
    speed: string;
    abilities: Record<string, number | null>;
    attacks: Array<Record<string, unknown>>;
    notes: string;
    monster_template_id: number | null;
  }>;
};
export type Campaign = CampaignSummary & {
  use_shared_exp: boolean;
  shared_experience: number;
  calendar: CampaignCalendar;
  party_money: Record<string, number | string>;
  characters: Character[];
};
export type CompendiumSource = {
  id: number;
  identifier: string;
  name: string;
  repository: string;
  campaign_id: number | null;
  enabled: boolean;
  entry_count: number;
};
export type CompendiumRepository = {
  id: string;
  name: string;
  description: string;
  tags: string[];
  repository_url: string;
  github_repository: string;
  installed: boolean;
};
export type LedgerEntry = {
  account_id: number;
  account_name: string;
  is_system_account: boolean;
  amount: number;
  item_id?: number;
  item_name?: string;
  denomination?: string;
};
export type LedgerTransaction = {
  id: number;
  ledger: string;
  description: string;
  created_at: string;
  entries: LedgerEntry[];
  reversal_of_id: number | null;
  is_reversed: boolean;
  reason?: string;
  requested_amount?: number;
  discarded_amount?: number;
  actor: string | null;
};

let csrfToken = "";

function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const cookie = document.cookie
    .split("; ")
    .find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getCookie("csrftoken") || csrfToken;
  const unsafe = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(options.method ?? "GET");
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body && !(options.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(unsafe ? { "X-CSRFToken": token } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(apiErrorMessage(error, response.statusText));
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object" || !("detail" in error)) return fallback;
  const { detail } = error as { detail: unknown };
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (typeof entry === "string") return entry;
      if (entry && typeof entry === "object" && "msg" in entry) {
        const { msg } = entry as { msg: unknown };
        if (typeof msg === "string") return msg;
      }
      return "";
    });
    return messages.filter(Boolean).join(" ") || fallback;
  }
  return fallback;
}

export async function initialiseCsrf(): Promise<void> {
  const response = await request<{ csrfToken: string }>("/api/auth/csrf/");
  csrfToken = getCookie("csrftoken") || response.csrfToken;
}
export const getSession = () => request<User>("/api/auth/session/");
export const login = (username: string, password: string) =>
  request<User>("/api/auth/session/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
export const logout = () => request<void>("/api/auth/session/", { method: "DELETE" });
export const getContexts = () => request<CampaignContext[]>("/api/contexts/");
export const getCampaigns = async (): Promise<CampaignSummary[]> => {
  const contexts = await getContexts();
  const campaigns = new Map<number, CampaignSummary>();
  for (const context of contexts) {
    const previous = campaigns.get(context.campaign_id);
    campaigns.set(context.campaign_id, {
      id: context.campaign_id,
      name: context.campaign_name,
      is_game_master: Boolean(previous?.is_game_master || context.kind === "gm"),
    });
  }
  return [...campaigns.values()];
};
export const getCampaign = (id: number) => request<Campaign>(`/api/contexts/${id}/`);
export const getCalendar = (id: number) =>
  request<CampaignCalendar>(`/api/contexts/${id}/calendar/`);
export const adjustCalendar = (id: number, amount: -1 | 1) =>
  request<CampaignCalendar>(`/api/contexts/${id}/calendar/adjust/`, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });

async function compendiumRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const campaign = await getCampaign(contextId);
  await ensureCampaignRealtime(campaign.id);
  return campaignRequest<T>(type, payload);
}

export const getItems = (id: number) => getCompendiumItemPages(id);

type CompendiumItemPage = {
  items: Item[];
  next_offset: number | null;
};

async function getCompendiumItemPages(contextId: number): Promise<Item[]> {
  const campaign = await getCampaign(contextId);
  await ensureCampaignRealtime(campaign.id);
  const items: Item[] = [];
  let nextOffset: number | null = 0;
  while (nextOffset !== null) {
    const page: CompendiumItemPage = await campaignRequest<CompendiumItemPage>(
      "compendium.items.list",
      { offset: nextOffset, limit: 100 },
    );
    items.push(...page.items);
    nextOffset = page.next_offset;
  }
  return items;
}

export const getCompendiumSources = (id: number) =>
  compendiumRequest<CompendiumSource[]>(id, "compendium.sources.list");
export const enableCompendiumSource = (id: number, sourceId: number) =>
  compendiumRequest<CompendiumSource>(id, "compendium.sources.enable", {
    source_id: sourceId,
  });
export const disableCompendiumSource = (id: number, sourceId: number) =>
  compendiumRequest<void>(id, "compendium.sources.disable", {
    source_id: sourceId,
  });
export const getCompendiumRepositories = (id: number) => {
  return compendiumRequest<CompendiumRepository[]>(id, "compendium.repositories.list");
};
export const addMember = (id: number, username: string, isGameMaster = false) =>
  request<CampaignMember>(`/api/contexts/${id}/manage/contexts/`, {
    method: "POST",
    body: JSON.stringify({ username, kind: isGameMaster ? "gm" : "pc" }),
  });
export const updateMember = (
  campaignId: number,
  memberId: number,
  isGameMaster: boolean,
) =>
  request<CampaignMember>(`/api/contexts/${campaignId}/manage/contexts/${memberId}/`, {
    method: "PATCH",
    body: JSON.stringify({ is_game_master: isGameMaster }),
  });
export const removeMember = (campaignId: number, memberId: number) =>
  request<void>(`/api/contexts/${campaignId}/manage/contexts/${memberId}/`, {
    method: "DELETE",
  });
export const createItem = (
  id: number,
  name: string,
  description: string,
  metadata: Partial<EquipmentMetadata> = {},
): Promise<Item> => {
  return compendiumRequest<Item>(id, "compendium.items.create", {
    name,
    description,
    metadata,
  });
};
export const updateItem = (
  campaignId: number,
  itemId: number,
  payload: {
    name?: string;
    description?: string;
    metadata?: Partial<EquipmentMetadata>;
  },
) => {
  return compendiumRequest<Item>(campaignId, "compendium.items.update", {
    item_id: itemId,
    ...payload,
  });
};
export const deleteItem = (campaignId: number, itemId: number) => {
  return compendiumRequest<void>(campaignId, "compendium.items.delete", {
    item_id: itemId,
  });
};
export const getCharacters = (campaignId: number) =>
  request<Character[]>(`/api/contexts/${campaignId}/characters/`);
export const getMyCharacters = (contextId: number) =>
  getCharacters(contextId).then((characters) =>
    characters.filter((character) => character.context_id === contextId),
  );
export const getMembers = (contextId: number) =>
  request<CampaignMember[]>(`/api/contexts/${contextId}/manage/contexts/`);
export const createCharacter = (
  campaignId: number,
  payload: {
    name: string;
    race: string;
    character_class: string;
    strength: number;
    dexterity: number;
    constitution: number;
    intelligence: number;
    wisdom: number;
    charisma: number;
    is_npc?: boolean;
  },
) =>
  request<Character>(`/api/contexts/${campaignId}/characters/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const archiveCharacter = (campaignId: number, characterId: number) =>
  request<Character>(`/api/contexts/${campaignId}/characters/${characterId}/`, {
    method: "DELETE",
  });
export type CahPreview = {
  token: string;
  fields: Record<string, unknown>;
  collections: Record<string, Array<Record<string, unknown>>>;
  inventory: Array<{
    line_id: string;
    name: string;
    kind: string;
    description: string;
    quantity: number;
    equipped: boolean;
    matched_item_id: number | null;
    action: "add" | "leave";
  }>;
  warnings: string[];
  calculated_before: Record<string, unknown> | null;
  calculated_after: Record<string, unknown> | null;
};
export const previewCahImport = (
  contextId: number,
  characterId: number,
  file: File,
) => {
  const body = new FormData();
  body.append("file", file);
  return request<CahPreview>(
    `/api/contexts/${contextId}/character-imports/cah/preview?character_id=${characterId}`,
    { method: "POST", body },
  );
};
export const commitCahImport = (
  contextId: number,
  token: string,
  characterId?: number,
  inventory: Array<{
    line_id: string;
    action: "add" | "leave";
    quantity: number;
    item_id?: number;
  }> = [],
) =>
  request<Character>(`/api/contexts/${contextId}/character-imports/cah/commit`, {
    method: "POST",
    body: JSON.stringify({ token, character_id: characterId, inventory }),
  });
export const updateCharacter = (
  campaignId: number,
  characterId: number,
  payload: Record<string, unknown>,
) => {
  const { class: characterClass, ...fields } = payload as {
    class?: string;
  } & Record<string, unknown>;
  return request<Character>(`/api/contexts/${campaignId}/characters/${characterId}/`, {
    method: "PATCH",
    body: JSON.stringify({ ...fields, character_class: characterClass }),
  });
};
export type InventoryTransactionInput = {
  from_character_id: number | null;
  to_character_id: number | null;
  item_id: number;
  quantity: number;
  description?: string;
};
export type MoneyTransferInput = {
  from_character_id: number | null;
  to_character_id: number | null;
  amounts: Record<string, number>;
  description?: string;
};
export type MoneyExchangeInput = {
  character_id: number;
  given: Record<string, number>;
  received: Record<string, number>;
  description?: string;
};

export const createInventoryTransaction = (
  campaignId: number,
  payload: InventoryTransactionInput,
) =>
  request<LedgerTransaction>(`/api/contexts/${campaignId}/inventory-transactions/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const createMoneyTransfer = (campaignId: number, payload: MoneyTransferInput) =>
  request<LedgerTransaction>(`/api/contexts/${campaignId}/money-transfers/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const createMoneyExchange = (campaignId: number, payload: MoneyExchangeInput) =>
  request<LedgerTransaction>(`/api/contexts/${campaignId}/money-exchanges/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const createSharedXpAward = (
  campaignId: number,
  payload: { amount: number; description?: string },
) =>
  request<LedgerTransaction>(`/api/contexts/${campaignId}/shared-xp-awards/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const getTransactions = (
  campaignId: number,
  ledger = "all",
  page = 1,
  characterId?: number,
) =>
  request<{
    count: number;
    page: number;
    page_size: number;
    results: LedgerTransaction[];
  }>(
    `/api/contexts/${campaignId}/transactions/?ledger=${ledger}&page=${page}${
      characterId ? `&character_id=${characterId}` : ""
    }`,
  );
export const reverseTransaction = (
  campaignId: number,
  transaction: LedgerTransaction,
) => {
  return request(
    `/api/contexts/${campaignId}/transactions/${transaction.ledger}/${transaction.id}/`,
    { method: "DELETE" },
  );
};
