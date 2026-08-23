import {
  campaignRequest,
  campaignImportRequest,
  ensureCampaignRealtime,
  inviteRequest,
  userRequest,
} from "./realtime";

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
  race_entry_id: number | null;
  class: string;
  background: string;
  background_entry_id: number | null;
  subrace: string;
  alignment: string;
  personality_traits: string;
  ideals: string;
  bonds: string;
  flaws: string;
  about: string;
  languages: string[];
  equipment_proficiencies: Record<string, string[]>;
  is_build_complete: boolean;
  level_up_complete: boolean;
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
    hp_calculation: Calculation;
    current_hp: number;
    temporary_hp: number;
    base_ac: number;
    ac_adjustment: number;
    armor_class: number;
    armor_class_calculation: Calculation;
    speed: string;
    spell_slots: Record<string, number>;
    proficiency_bonus_adjustment: number;
    proficiency_bonus: number;
    proficiency_bonus_calculation: Calculation;
    abilities: Record<
      string,
      {
        score: number;
        raw: number;
        ancestry_bonus: number;
        score_adjustment: number;
        modifier: number;
        adjustment: number;
        formula: Calculation;
      }
    >;
    saves: Record<
      string,
      { proficient: boolean; adjustment: number; bonus: number; formula: Calculation }
    >;
    skills: Record<
      string,
      { proficiency: string; bonus: number; formula: Calculation }
    >;
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
export type Calculation = {
  value: number;
  base: number;
  formula?: string;
  components: Array<{
    label: string;
    value: number;
    formula?: string;
    source?: string;
  }>;
};
export type Campaign = CampaignSummary & {
  use_shared_exp: boolean;
  shared_experience: number;
  level: number;
  eligible_level: number;
  incomplete_level_ups: Array<{
    character_id: number;
    character_name: string;
    level: number;
  }>;
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
  ledger_label?: string;
  description: string;
  created_at: string;
  occurred_at: string;
  campaign_date: string | null;
  entries: LedgerEntry[];
  reversal_of_id: number | null;
  is_reversed: boolean;
  reason?: string;
  requested_amount?: number;
  discarded_amount?: number;
  actor: string | null;
  character_name?: string;
  changes?: Record<string, { before: unknown; after: unknown }>;
  current_hp_delta?: number;
  temporary_hp_delta?: number;
  current_hp_before?: number;
  current_hp_after?: number;
  temporary_hp_before?: number;
  temporary_hp_after?: number;
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
export const getContexts = () => userRequest<CampaignContext[]>("user.contexts.list");
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
export const getCampaign = async (id: number) => {
  await ensureCampaignRealtime(id);
  return campaignRequest<Campaign>("campaign.get");
};
export const getCalendar = (id: number) =>
  contextRequest<CampaignCalendar>(id, "campaign.calendar.get");
export const adjustCalendar = (id: number, amount: -1 | 1) =>
  contextRequest<CampaignCalendar>(id, "campaign.calendar.adjust", { amount });

async function contextRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  await ensureCampaignRealtime(contextId);
  return campaignRequest<T>(type, payload);
}

async function compendiumRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  return contextRequest<T>(contextId, type, payload);
}

export const getItems = (id: number) => getCompendiumItemPages(id);

type CompendiumItemPage = {
  items: Item[];
  next_offset: number | null;
};

async function getCompendiumItemPages(contextId: number): Promise<Item[]> {
  await ensureCampaignRealtime(contextId);
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
export const removeMember = (campaignId: number, memberId: number) =>
  contextRequest<void>(campaignId, "campaign.members.deactivate", {
    member_id: memberId,
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
  contextRequest<Character[]>(campaignId, "characters.list");
export const getMyCharacters = (contextId: number) =>
  getCharacters(contextId).then((characters) =>
    characters.filter((character) => character.context_id === contextId),
  );
export const getMembers = (contextId: number) =>
  contextRequest<CampaignMember[]>(contextId, "campaign.members.list");
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
) => contextRequest<Character>(campaignId, "characters.create", { fields: payload });
export const archiveCharacter = (campaignId: number, characterId: number) =>
  contextRequest<Character>(campaignId, "characters.archive", {
    character_id: characterId,
  });
export type CahPreview = {
  token: string;
  field_changes: Array<{
    field: string;
    before: unknown;
    after: unknown;
    changed: boolean;
    enabled?: boolean;
  }>;
  collection_changes: Array<{
    collection: string;
    before_count: number;
    after_count: number;
    names: string[];
    remaining_count: number;
    enabled?: boolean;
  }>;
  inventory: Array<{
    line_id: string;
    name: string;
    kind: string;
    description: string;
    quantity: number;
    equipped: boolean;
    matched_item_id: number | null;
    suggested_item_id: number | null;
    action: "add" | "leave";
  }>;
  warnings: string[];
  calculated_before: Record<string, Calculation | Record<string, Calculation>> | null;
  calculated_after: Record<string, Calculation | Record<string, Calculation>> | null;
};
export const previewCahImport = (
  contextId: number,
  characterId: number,
  file: File,
) => {
  return previewCahImportOverSocket(contextId, characterId, file);
};

async function previewCahImportOverSocket(
  contextId: number,
  characterId: number,
  file: File,
): Promise<CahPreview> {
  const upload = await contextRequest<{
    upload_id: string;
    upload_url: string;
  }>(contextId, "characters.imports.cah.begin", { character_id: characterId });
  const body = new FormData();
  body.append("file", file);
  await request<void>(upload.upload_url, { method: "POST", body });
  await ensureCampaignRealtime(contextId);
  return campaignImportRequest<CahPreview>("characters.imports.cah.preview", {
    upload_id: upload.upload_id,
  });
}

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
  fields: Record<string, unknown> = {},
  excludedFields: string[] = [],
  collections: Record<string, boolean> = {},
) => {
  return ensureCampaignRealtime(contextId).then(() =>
    campaignImportRequest<Character>("characters.imports.cah.commit", {
      token,
      character_id: characterId,
      inventory,
      fields,
      excluded_fields: excludedFields,
      collections,
    }),
  );
};
export const cancelCahImport = (contextId: number, token: string) =>
  contextRequest<void>(contextId, "characters.imports.cah.cancel", { token });
export const updateCharacter = (
  campaignId: number,
  characterId: number,
  payload: Record<string, unknown>,
) => {
  const { class: characterClass, ...fields } = payload as {
    class?: string;
  } & Record<string, unknown>;
  return contextRequest<Character>(campaignId, "characters.update", {
    character_id: characterId,
    fields: { ...fields, character_class: characterClass },
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
  contextRequest<LedgerTransaction>(
    campaignId,
    "inventory.transactions.create",
    payload,
  );
export const createMoneyTransfer = (campaignId: number, payload: MoneyTransferInput) =>
  contextRequest<LedgerTransaction>(campaignId, "money.transfers.create", payload);
export const createMoneyExchange = (campaignId: number, payload: MoneyExchangeInput) =>
  contextRequest<LedgerTransaction>(campaignId, "money.exchanges.create", payload);
export const createSharedXpAward = (
  campaignId: number,
  payload: { amount: number; description?: string },
) =>
  contextRequest<LedgerTransaction>(
    campaignId,
    "experience.shared_awards.create",
    payload,
  );
export const getTransactions = (
  campaignId: number,
  ledger = "all",
  page = 1,
  characterId?: number,
) =>
  contextRequest<{
    count: number;
    page: number;
    page_size: number;
    results: LedgerTransaction[];
  }>(campaignId, "transactions.list", {
    ledger,
    page,
    ...(characterId ? { character_id: characterId } : {}),
  });
export const reverseTransaction = (
  campaignId: number,
  transaction: LedgerTransaction,
) => {
  return contextRequest(campaignId, "transactions.reverse", {
    ledger: transaction.ledger,
    transaction_id: transaction.id,
  });
};

export type CampaignInvitation = {
  id: number;
  email: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  status: "pending" | "accepted" | "expired" | "revoked";
  link?: string;
};

export const getInvitations = (contextId: number) =>
  contextRequest<CampaignInvitation[]>(contextId, "campaign.invites.list");
export const createInvitation = (contextId: number, email = "") =>
  contextRequest<CampaignInvitation>(contextId, "campaign.invites.create", { email });
export const resendInvitation = (contextId: number, invitationId: number) =>
  contextRequest<CampaignInvitation>(contextId, "campaign.invites.resend", {
    invitation_id: invitationId,
  });
export const revokeInvitation = (contextId: number, invitationId: number) =>
  contextRequest<void>(contextId, "campaign.invites.revoke", {
    invitation_id: invitationId,
  });

export type InviteDetails = {
  campaign_name: string;
  expires_at: string;
  authenticated: boolean;
  username: string | null;
};
export const inspectInvite = (token: string) =>
  inviteRequest<InviteDetails>(token, "invite.inspect");
export const acceptInvite = (token: string) =>
  inviteRequest<{ context_id: number; character_id: number }>(token, "invite.accept");
export const registerAndAcceptInvite = (
  token: string,
  payload: { username: string; email: string; password: string },
) =>
  inviteRequest<{
    context_id: number;
    character_id: number;
    username: string;
  }>(token, "invite.register_and_accept", payload);

export const approveCampaignLevel = (contextId: number) =>
  contextRequest(contextId, "campaign.level.approve");

export const postHealth = (
  contextId: number,
  payload: {
    character_id: number;
    reason: "damage" | "healing" | "temporary" | "correction";
    current_hp_delta?: number;
    temporary_hp_delta?: number;
    current_hp?: number;
    temporary_hp?: number;
    description?: string;
  },
) => contextRequest<LedgerTransaction>(contextId, "characters.health.post", payload);

export const changeCharacterSheetRecord = (
  contextId: number,
  characterId: number,
  resource: "notes" | "features" | "spells" | "loadout" | "companions",
  operation: "create" | "update" | "delete",
  fields: Record<string, unknown> = {},
  recordId?: number,
) =>
  contextRequest<Record<string, unknown> | null>(
    contextId,
    `characters.${resource}.${operation}`,
    {
      character_id: characterId,
      fields,
      ...(recordId === undefined ? {} : { record_id: recordId }),
    },
  );

export type BuilderEntry = {
  id: number;
  alias_ids?: number[];
  identifier: string;
  name: string;
  source: string;
  source_book: string;
  repository: string;
  repository_identifier: string;
  data?: Record<string, unknown>;
};
export type BuilderDefinition = {
  level: number;
  race: BuilderEntry[];
  class: BuilderEntry[];
  background: BuilderEntry[];
  skills: string[];
};
export const getBuilderDefinition = (contextId: number) =>
  contextRequest<BuilderDefinition>(contextId, "characters.builder.definition");
export const getBuilderEntry = (contextId: number, entryId: number) =>
  contextRequest<BuilderEntry & { kind: "race" | "class" | "background" }>(
    contextId,
    "characters.builder.entry.get",
    { entry_id: entryId },
  );
export const getCharacterBuilder = (contextId: number, characterId: number) =>
  contextRequest<Record<string, unknown>>(contextId, "characters.builder.get", {
    character_id: characterId,
  });
export const saveCharacterBuilder = (
  contextId: number,
  characterId: number,
  payload: Record<string, unknown>,
) =>
  contextRequest<Character>(contextId, "characters.builder.save", {
    character_id: characterId,
    ...payload,
  });
export const completeCharacterBuilder = (contextId: number, characterId: number) =>
  contextRequest<Character>(contextId, "characters.builder.complete", {
    character_id: characterId,
  });

export type LevelUpDefinition = {
  character: Character;
  level: number;
  preferred_class_ids: number[];
  classes: Array<
    Pick<BuilderEntry, "id" | "name" | "source" | "source_book" | "identifier">
  >;
};
export type LevelUpRules = {
  class: {
    id: number;
    name: string;
    source: string;
    source_book: string;
    class_level: number;
    hit_die: number;
    average_hp: number;
    subclass_required: boolean;
    subclasses: Array<{
      identifier: string;
      name: string;
      source: string;
      level: number;
    }>;
  };
  gains: Array<{ name: string; identifier: string; description: string }>;
  ability_score_improvement: boolean;
  choices: Array<{
    identifier: string;
    name: string;
    amount: number;
    options: Array<{ name: string; identifier: string; description: string }>;
  }>;
};
export type LevelUpPreview = {
  rules: LevelUpRules;
  before: Character["sheet"];
  after: Character["sheet"];
};
export const getLevelUpDefinition = (contextId: number, characterId: number) =>
  contextRequest<LevelUpDefinition>(contextId, "characters.level_up.definition", {
    character_id: characterId,
  });
export const getLevelUpClass = (
  contextId: number,
  characterId: number,
  classEntryId: number,
) =>
  contextRequest<LevelUpRules>(contextId, "characters.level_up.class.get", {
    character_id: characterId,
    class_entry_id: classEntryId,
  });
export const previewLevelUp = (
  contextId: number,
  characterId: number,
  payload: {
    class_entry_id: number;
    hp_increase?: number;
    ability_adjustments?: Record<string, number>;
  },
) =>
  contextRequest<LevelUpPreview>(contextId, "characters.level_up.preview", {
    character_id: characterId,
    ...payload,
  });
export type LevelUpFeat = {
  id: number;
  name: string;
  source: string;
  source_book: string;
};
export const getLevelUpFeats = (contextId: number, characterId: number, query = "") =>
  contextRequest<LevelUpFeat[]>(contextId, "characters.level_up.feats", {
    character_id: characterId,
    query,
  });
export const completeLevelUp = (
  contextId: number,
  characterId: number,
  payload: Record<string, unknown>,
) =>
  contextRequest<Character>(contextId, "characters.level_up.complete", {
    character_id: characterId,
    ...payload,
  });
