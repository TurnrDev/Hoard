export type User = { id: number; username: string };
export type CampaignSummary = {
  id: number;
  name: string;
  is_game_master: boolean;
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
  name: string;
  is_player_character: boolean;
  is_active: boolean;
  is_archived: boolean;
  archived_at: string | null;
  race: string;
  class: string;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  experience: number;
  money: Record<string, number | string>;
  inventory: Array<{ item_id: number; name: string; quantity: number }>;
};
export type Campaign = CampaignSummary & {
  use_shared_exp: boolean;
  shared_experience: number;
  item_sources: string[];
  party_money: Record<string, number | string>;
  characters: Character[];
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
  const unsafe = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(
    options.method ?? "GET",
  );
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(unsafe ? { "X-CSRFToken": token } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string" ? error.detail : JSON.stringify(error),
    );
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
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
export const logout = () =>
  request<void>("/api/auth/session/", { method: "DELETE" });
export const getCampaigns = () => request<CampaignSummary[]>("/api/campaigns/");
export const getCampaign = (id: number) =>
  request<Campaign>(`/api/campaigns/${id}/`);
export const getItems = (id: number) =>
  request<Item[]>(`/api/campaigns/${id}/items/`);
export const getMembers = (id: number) =>
  request<CampaignMember[]>(`/api/campaigns/${id}/members/`);
export const addMember = (id: number, username: string, isGameMaster = false) =>
  request<CampaignMember>(`/api/campaigns/${id}/members/`, {
    method: "POST",
    body: JSON.stringify({ username, is_game_master: isGameMaster }),
  });
export const updateMember = (
  campaignId: number,
  memberId: number,
  isGameMaster: boolean,
) =>
  request<CampaignMember>(`/api/campaigns/${campaignId}/members/${memberId}/`, {
    method: "PATCH",
    body: JSON.stringify({ is_game_master: isGameMaster }),
  });
export const removeMember = (campaignId: number, memberId: number) =>
  request<void>(`/api/campaigns/${campaignId}/members/${memberId}/`, {
    method: "DELETE",
  });
export const createItem = (
  id: number,
  name: string,
  description: string,
  metadata: Partial<EquipmentMetadata> = {},
) =>
  request<Item>(`/api/campaigns/${id}/items/`, {
    method: "POST",
    body: JSON.stringify({ name, description, metadata }),
  });
export const updateItem = (
  campaignId: number,
  itemId: number,
  payload: {
    name?: string;
    description?: string;
    metadata?: Partial<EquipmentMetadata>;
  },
) =>
  request<Item>(`/api/campaigns/${campaignId}/items/${itemId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const deleteItem = (campaignId: number, itemId: number) =>
  request<void>(`/api/campaigns/${campaignId}/items/${itemId}/`, {
    method: "DELETE",
  });
export const getCharacters = (campaignId: number) =>
  request<Character[]>(`/api/campaigns/${campaignId}/characters/`);
export const getMyCharacters = (campaignId: number) =>
  request<Character[]>(`/api/campaigns/${campaignId}/characters/me/`);
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
    player_id?: number | null;
  },
) =>
  request<Character>(`/api/campaigns/${campaignId}/characters/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const archiveCharacter = (campaignId: number, characterId: number) =>
  request<Character>(
    `/api/campaigns/${campaignId}/characters/${characterId}/`,
    { method: "DELETE" },
  );
export const updateCharacter = (
  campaignId: number,
  characterId: number,
  payload: Partial<
    Pick<
      Character,
      | "name"
      | "race"
      | "class"
      | "is_active"
      | "strength"
      | "dexterity"
      | "constitution"
      | "intelligence"
      | "wisdom"
      | "charisma"
    >
  >,
) => {
  const { class: characterClass, ...fields } = payload;
  return request<Character>(
    `/api/campaigns/${campaignId}/characters/${characterId}/`,
    {
      method: "PATCH",
      body: JSON.stringify({ ...fields, character_class: characterClass }),
    },
  );
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
  request<LedgerTransaction>(
    `/api/campaigns/${campaignId}/inventory-transactions/`,
    { method: "POST", body: JSON.stringify(payload) },
  );
export const createMoneyTransfer = (
  campaignId: number,
  payload: MoneyTransferInput,
) =>
  request<LedgerTransaction>(`/api/campaigns/${campaignId}/money-transfers/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const createMoneyExchange = (
  campaignId: number,
  payload: MoneyExchangeInput,
) =>
  request<LedgerTransaction>(`/api/campaigns/${campaignId}/money-exchanges/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const createSharedXpAward = (
  campaignId: number,
  payload: { amount: number; description?: string },
) =>
  request<LedgerTransaction>(`/api/campaigns/${campaignId}/shared-xp-awards/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const getTransactions = (campaignId: number, ledger = "all", page = 1) =>
  request<{
    count: number;
    page: number;
    page_size: number;
    results: LedgerTransaction[];
  }>(
    `/api/campaigns/${campaignId}/transactions/?ledger=${ledger}&page=${page}`,
  );
export const reverseTransaction = (
  campaignId: number,
  transaction: LedgerTransaction,
) => {
  return request(
    `/api/campaigns/${campaignId}/transactions/${transaction.ledger}/${transaction.id}/`,
    { method: "DELETE" },
  );
};
