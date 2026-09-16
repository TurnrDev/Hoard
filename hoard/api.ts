import axios from "axios";
import { markConnectionAvailable, markConnectionUnavailable } from "./connection";
import {
  campaignImportRequest,
  campaignRequest,
  ensureCampaignRealtime,
  inviteRequest,
  userRequest,
} from "./realtime";

export type User = {
  id: number;
  username: string;
};

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
  first_name: string;
  last_name: string;
  is_game_master: boolean;
  is_active: boolean;
  connected: boolean;
  last_seen_at: string | null;
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

export type CalculationComponent = {
  label: string;
  value: number;
  formula?: string;
  source?: string;
};

export type Calculation = {
  value: number;
  base: number;
  formula?: string;
  numeric_formula?: string;
  components: CalculationComponent[];
};

export type SpellSlotPool = {
  calculated: number;
  adjustment: number;
  maximum: number;
  current: number;
};

export type CharacterAbility = {
  score: number;
  raw: number;
  ancestry_bonus: number;
  score_adjustment: number;
  modifier: number;
  adjustment: number;
  formula: Calculation;
};

export type CharacterSave = {
  proficient: boolean;
  adjustment: number;
  bonus: number;
  formula: Calculation;
};

export type CharacterSkill = {
  proficiency: string;
  bonus: number;
  formula: Calculation;
};

export type CharacterSheet = {
  level: number;
  base_hp: number;
  hp_ability: string;
  max_hp: number;
  hp_calculation: Calculation;
  current_hp: number;
  temporary_hp: number;
  base_ac: number;
  ac_adjustment: number;
  armor_class: number;
  armor_class_calculation: Calculation;
  speed: string;
  spell_slot_pools: Record<string, SpellSlotPool>;
  spell_attack: number;
  spell_save_dc: number;
  initiative: Calculation;
  proficiency_bonus_adjustment: number;
  proficiency_bonus: number;
  proficiency_bonus_calculation: Calculation;
  abilities: Record<string, CharacterAbility>;
  saves: Record<string, CharacterSave>;
  skills: Record<string, CharacterSkill>;
};

export type CharacterInventoryItem = {
  item_id: number;
  name: string;
  quantity: number;
};

export type CharacterNote = {
  id: number;
  body: string;
};

export type CharacterFeature = {
  id: number;
  kind: string;
  name: string;
  description: string;
  notes: string;
  catalogue_entry_id: number | null;
};

export type CharacterSpell = {
  id: number;
  name: string;
  level: number;
  description: string;
  notes: string;
  prepared: boolean;
  catalogue_entry_id: number | null;
};

export type CharacterLoadoutItem = {
  id: number;
  item_id: number;
  name: string;
  equipped: boolean;
  slot: "armor" | "shield" | "weapon" | "other";
  label: string;
};

export type CharacterEffectModifier = {
  target: string;
  value: number;
  label: string;
};

export type CharacterEffect = {
  id: number;
  source: string;
  name: string;
  enabled: boolean;
  duration: string;
  reminder: string;
  expires_on_rest: "manual" | "short" | "long";
  modifiers: CharacterEffectModifier[];
};

export type CharacterCompanion = {
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
};

export type ConditionIdentifier =
  | "blinded"
  | "charmed"
  | "deafened"
  | "exhaustion"
  | "frightened"
  | "grappled"
  | "incapacitated"
  | "invisible"
  | "paralyzed"
  | "petrified"
  | "poisoned"
  | "prone"
  | "restrained"
  | "stunned"
  | "unconscious"
  | "pacify";

export type ConditionInstance = {
  id: number;
  source: string;
  duration: string;
};

export type ActiveCondition = {
  id: ConditionIdentifier;
  label: string;
  exhaustion_level: number | null;
  source: string;
  duration: string;
  instances: ConditionInstance[];
};

export type EncounterCombatant = {
  id: number;
  character_id: number | null;
  creature_entry_id: number | null;
  is_player_character: boolean;
  name: string;
  portrait_url: string | null;
  initiative: number;
  initiative_position: number;
  initiative_roll: number | null;
  initiative_modifier: number;
  can_roll_initiative: boolean;
  can_end_turn: boolean;
  tie_options: Array<{ combatant_id: number; name: string; vote_count: number }>;
  tie_choice_id: number | null;
  tie_votes_cast: number;
  tie_votes_required: number;
  tie_winner_id: number | null;
  tie_resolution: "agreement" | "random" | null;
  current_hp: number | null;
  max_hp: number | null;
  health_percentage: number | null;
  show_hp_numbers: boolean;
  has_inspiration: boolean;
  conditions: ActiveCondition[];
};

export type Encounter = {
  id: number;
  started_at: string;
  current_combatant_id: number | null;
  combatants: EncounterCombatant[];
};

export type CompendiumSearchEntry = {
  id: number;
  name: string;
  description: string;
  kind: string;
  source: string;
};

export type EncounterCombatantInput = {
  name: string;
  creature_entry_id?: number;
  initiative: number;
  current_hp?: number;
  max_hp?: number;
};

export type ConditionMutation = {
  condition_id?: number;
  identifier: ConditionIdentifier;
  source: string;
  duration: string;
  exhaustion_level?: number;
};

export type Character = {
  id: number;
  context_id: number | null;
  name: string;
  portrait_url: string | null;
  kind: "pc" | "npc";
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
  has_inspiration: boolean;
  inspiration_expires_at: string | null;
  conditions: ActiveCondition[];
  is_build_complete: boolean;
  level_up_complete: boolean;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  sheet: CharacterSheet;
  experience: number;
  money: Record<string, number | string>;
  inventory: CharacterInventoryItem[];
  notes: CharacterNote[];
  features: CharacterFeature[];
  spells: CharacterSpell[];
  loadout: CharacterLoadoutItem[];
  effects: CharacterEffect[];
  companions: CharacterCompanion[];
};

export type IncompleteLevelUp = {
  character_id: number;
  character_name: string;
  level: number;
};

export type Campaign = CampaignSummary & {
  shared_experience: number;
  level: number;
  eligible_level: number;
  incomplete_level_ups: IncompleteLevelUp[];
  calendar: CampaignCalendar;
  party_money: Record<string, number | string>;
  encounter: Encounter | null;
  members: CampaignMember[];
  characters: Character[];
  invitations: CampaignInvitation[];
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
  condition?: string;
  condition_instance_id?: number;
  encounter_id?: number | null;
  changes?: Record<string, { before: unknown; after: unknown }>;
  current_hp_delta?: number;
  temporary_hp_delta?: number;
  current_hp_before?: number;
  current_hp_after?: number;
  temporary_hp_before?: number;
  temporary_hp_after?: number;
};

let csrfToken = "";
const http = axios.create({
  headers: { Accept: "application/json" },
  withCredentials: true,
});

function getCookie(name: string): string {
  if (typeof document === "undefined") {
    return "";
  }
  const cookie = document.cookie
    .split("; ")
    .find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getCookie("csrftoken") || csrfToken;
  const unsafe = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(options.method ?? "GET");
  const headers = Object.fromEntries(new Headers(options.headers).entries());
  try {
    const response = await http.request<T>({
      url,
      method: options.method,
      data: options.body,
      headers: {
        ...headers,
        ...(options.body && !(options.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(unsafe ? { "X-CSRFToken": token } : {}),
      },
    });
    markConnectionAvailable("http");

    return response.status === 204 ? (undefined as T) : response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        markConnectionAvailable("http");
      } else {
        markConnectionUnavailable("http");
      }

      throw new Error(
        apiErrorMessage(
          error.response?.data,
          error.response?.statusText ?? error.message,
        ),
        { cause: error },
      );
    }
    throw error;
  }
}

export function isUnauthenticatedError(error: unknown): boolean {
  if (!(error instanceof Error) || !axios.isAxiosError(error.cause)) {
    return false;
  }

  return error.cause.response?.status === 401;
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object" || !("detail" in error)) {
    return fallback;
  }
  const { detail } = error as { detail: unknown };
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (typeof entry === "string") {
        return entry;
      }
      if (entry && typeof entry === "object" && "msg" in entry) {
        const { msg } = entry as { msg: unknown };
        if (typeof msg === "string") {
          return msg;
        }
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

export function getSession(): Promise<User> {
  return request<User>("/api/auth/session/");
}

export function login(username: string, password: string): Promise<User> {
  const credentials = JSON.stringify({ username, password });

  return request<User>("/api/auth/session/", {
    method: "POST",
    body: credentials,
  });
}

export function logout(): Promise<void> {
  return request<void>("/api/auth/session/", { method: "DELETE" });
}

export function getContexts(): Promise<CampaignContext[]> {
  return userRequest<CampaignContext[]>("user.contexts.list");
}

export async function getCampaigns(): Promise<CampaignSummary[]> {
  const contexts = await getContexts();
  const campaigns = new Map<number, CampaignSummary>();

  for (const context of contexts) {
    const previous = campaigns.get(context.campaign_id);
    const isGameMaster = previous?.is_game_master || context.kind === "gm";

    campaigns.set(context.campaign_id, {
      id: context.campaign_id,
      name: context.campaign_name,
      is_game_master: isGameMaster,
    });
  }

  return [...campaigns.values()];
}

export async function getCampaign(id: number): Promise<Campaign> {
  await ensureCampaignRealtime(id);

  return campaignRequest<Campaign>("campaign.get");
}

export function getCalendar(id: number): Promise<CampaignCalendar> {
  return contextRequest<CampaignCalendar>(id, "campaign.calendar.get");
}

export function adjustCalendar(id: number, amount: -1 | 1): Promise<void> {
  return contextRequest<void>(id, "campaign.calendar.adjust", {
    amount,
  });
}

async function contextRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  await ensureCampaignRealtime(contextId);
  return campaignRequest<T>(type, payload);
}

function compendiumRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  return contextRequest<T>(contextId, type, payload);
}

export function getItems(id: number): Promise<Item[]> {
  return getCompendiumItemPages(id);
}

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

export function getCompendiumSources(id: number): Promise<CompendiumSource[]> {
  return compendiumRequest<CompendiumSource[]>(id, "compendium.sources.list");
}

export function enableCompendiumSource(
  id: number,
  sourceId: number,
): Promise<CompendiumSource> {
  return compendiumRequest<CompendiumSource>(id, "compendium.sources.enable", {
    source_id: sourceId,
  });
}

export function disableCompendiumSource(id: number, sourceId: number): Promise<void> {
  return compendiumRequest<void>(id, "compendium.sources.disable", {
    source_id: sourceId,
  });
}

export function getCompendiumRepositories(id: number): Promise<CompendiumRepository[]> {
  return compendiumRequest<CompendiumRepository[]>(id, "compendium.repositories.list");
}

export function removeMember(campaignId: number, memberId: number): Promise<void> {
  return contextRequest<void>(campaignId, "campaign.members.deactivate", {
    member_id: memberId,
  });
}

export function createItem(
  id: number,
  name: string,
  description: string,
  metadata: Partial<EquipmentMetadata> = {},
): Promise<Item> {
  return compendiumRequest<Item>(id, "compendium.items.create", {
    name,
    description,
    metadata,
  });
}

export function updateItem(
  campaignId: number,
  itemId: number,
  payload: {
    name?: string;
    description?: string;
    metadata?: Partial<EquipmentMetadata>;
  },
): Promise<Item> {
  return compendiumRequest<Item>(campaignId, "compendium.items.update", {
    item_id: itemId,
    ...payload,
  });
}

export function deleteItem(campaignId: number, itemId: number): Promise<void> {
  return compendiumRequest<void>(campaignId, "compendium.items.delete", {
    item_id: itemId,
  });
}

export function getCharacters(campaignId: number): Promise<Character[]> {
  return contextRequest<Character[]>(campaignId, "characters.list");
}

export async function getMyCharacters(contextId: number): Promise<Character[]> {
  const characters = await getCharacters(contextId);

  return characters.filter((character) => character.context_id === contextId);
}

export function getMembers(contextId: number): Promise<CampaignMember[]> {
  return contextRequest<CampaignMember[]>(contextId, "campaign.members.list");
}

export function createCharacter(
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
): Promise<void> {
  return contextRequest<void>(campaignId, "characters.create", {
    fields: payload,
  });
}

export function archiveCharacter(
  campaignId: number,
  characterId: number,
): Promise<void> {
  return contextRequest<void>(campaignId, "characters.archive", {
    character_id: characterId,
  });
}
export type CahFieldChange = {
  field: string;
  before: unknown;
  after: unknown;
  changed: boolean;
  enabled?: boolean;
};

export type CahCollectionChange = {
  collection: string;
  before_count: number;
  after_count: number;
  names: string[];
  remaining_count: number;
  enabled?: boolean;
};

export type CahInventoryLine = {
  line_id: string;
  name: string;
  kind: string;
  description: string;
  quantity: number;
  equipped: boolean;
  matched_item_id: number | null;
  suggested_item_id: number | null;
  action: "add" | "leave";
};

export type CahInventorySelection = {
  line_id: string;
  action: "add" | "leave";
  quantity: number;
  item_id?: number;
};

export type CahUpload = {
  upload_id: string;
  upload_url: string;
};

export type CahPreview = {
  token: string;
  field_changes: CahFieldChange[];
  collection_changes: CahCollectionChange[];
  inventory: CahInventoryLine[];
  warnings: string[];
  calculated_before: Record<string, Calculation | Record<string, Calculation>> | null;
  calculated_after: Record<string, Calculation | Record<string, Calculation>> | null;
};
export function previewCahImport(
  contextId: number,
  characterId: number,
  file: File,
): Promise<CahPreview> {
  return previewCahImportOverSocket(contextId, characterId, file);
}

async function previewCahImportOverSocket(
  contextId: number,
  characterId: number,
  file: File,
): Promise<CahPreview> {
  const upload = await contextRequest<CahUpload>(
    contextId,
    "characters.imports.cah.begin",
    { character_id: characterId },
  );
  const body = new FormData();
  body.append("file", file);
  await request<void>(upload.upload_url, { method: "POST", body });
  await ensureCampaignRealtime(contextId);
  return campaignImportRequest<CahPreview>("characters.imports.cah.preview", {
    upload_id: upload.upload_id,
  });
}

export async function commitCahImport(
  contextId: number,
  token: string,
  characterId?: number,
  inventory: CahInventorySelection[] = [],
  fields: Record<string, unknown> = {},
  excludedFields: string[] = [],
  collections: Record<string, boolean> = {},
): Promise<Character> {
  await ensureCampaignRealtime(contextId);

  return campaignImportRequest<Character>("characters.imports.cah.commit", {
    token,
    character_id: characterId,
    inventory,
    fields,
    excluded_fields: excludedFields,
    collections,
  });
}

export function cancelCahImport(contextId: number, token: string): Promise<void> {
  return contextRequest<void>(contextId, "characters.imports.cah.cancel", { token });
}

export function updateCharacter(
  campaignId: number,
  characterId: number,
  payload: Record<string, unknown>,
): Promise<void> {
  const { class: characterClass, ...fields } = payload as {
    class?: string;
  } & Record<string, unknown>;

  return contextRequest<void>(campaignId, "characters.update", {
    character_id: characterId,
    fields: { ...fields, character_class: characterClass },
  });
}

export function uploadCharacterPortrait(
  contextId: number,
  characterId: number,
  file: File,
): Promise<{ portrait_url: string }> {
  const body = new FormData();
  body.append("file", file);

  return request<{ portrait_url: string }>(
    `/api/uploads/character-portraits/${contextId}/${characterId}/`,
    { method: "POST", body },
  );
}

export function removeCharacterPortrait(
  contextId: number,
  characterId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.portrait.remove", {
    character_id: characterId,
  });
}
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

export function createInventoryTransaction(
  campaignId: number,
  payload: InventoryTransactionInput,
): Promise<void> {
  return contextRequest<void>(campaignId, "inventory.transactions.create", payload);
}

export function createMoneyTransfer(
  campaignId: number,
  payload: MoneyTransferInput,
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    campaignId,
    "money.transfers.create",
    payload,
  );
}

export function createMoneyExchange(
  campaignId: number,
  payload: MoneyExchangeInput,
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    campaignId,
    "money.exchanges.create",
    payload,
  );
}

export function createSharedXpAward(
  campaignId: number,
  payload: { amount: number; description?: string },
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    campaignId,
    "experience.shared_awards.create",
    payload,
  );
}

export function getTransactions(
  campaignId: number,
  ledger = "all",
  page = 1,
  characterId?: number,
): Promise<{
  count: number;
  page: number;
  page_size: number;
  results: LedgerTransaction[];
}> {
  const payload = {
    ledger,
    page,
    ...(characterId ? { character_id: characterId } : {}),
  };

  return contextRequest<{
    count: number;
    page: number;
    page_size: number;
    results: LedgerTransaction[];
  }>(campaignId, "transactions.list", payload);
}

export function reverseTransaction(
  campaignId: number,
  transaction: LedgerTransaction,
): Promise<unknown> {
  return contextRequest(campaignId, "transactions.reverse", {
    ledger: transaction.ledger,
    transaction_id: transaction.id,
  });
}

export type CampaignInvitation = {
  id: number;
  email: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  status: "pending" | "accepted" | "expired" | "revoked";
  link?: string;
};

export function getInvitations(contextId: number): Promise<CampaignInvitation[]> {
  return contextRequest<CampaignInvitation[]>(contextId, "campaign.invites.list");
}

export function createInvitation(
  contextId: number,
  email = "",
): Promise<CampaignInvitation> {
  return contextRequest<CampaignInvitation>(contextId, "campaign.invites.create", {
    email,
  });
}

export function resendInvitation(
  contextId: number,
  invitationId: number,
): Promise<CampaignInvitation> {
  return contextRequest<CampaignInvitation>(contextId, "campaign.invites.resend", {
    invitation_id: invitationId,
  });
}

export function revokeInvitation(
  contextId: number,
  invitationId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.invites.revoke", {
    invitation_id: invitationId,
  });
}

export type InviteDetails = {
  campaign_name: string;
  expires_at: string;
  authenticated: boolean;
  username: string | null;
};
export function inspectInvite(token: string): Promise<InviteDetails> {
  return inviteRequest<InviteDetails>(token, "invite.inspect");
}

export function acceptInvite(
  token: string,
): Promise<{ context_id: number; character_id: number }> {
  return inviteRequest<{ context_id: number; character_id: number }>(
    token,
    "invite.accept",
  );
}

export function registerAndAcceptInvite(
  token: string,
  payload: { username: string; email: string; password: string },
): Promise<{
  context_id: number;
  character_id: number;
  username: string;
}> {
  return inviteRequest<{
    context_id: number;
    character_id: number;
    username: string;
  }>(token, "invite.register_and_accept", payload);
}

export function approveCampaignLevel(contextId: number): Promise<unknown> {
  return contextRequest(contextId, "campaign.level.approve");
}

export function postHealth(
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
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    contextId,
    "characters.health.post",
    payload,
  );
}

export function changeCharacterSheetRecord(
  contextId: number,
  characterId: number,
  resource: "notes" | "features" | "spells" | "loadout" | "companions" | "effects",
  operation: "create" | "update" | "delete",
  fields: Record<string, unknown> = {},
  recordId?: number,
): Promise<Record<string, unknown> | null> {
  const payload = {
    character_id: characterId,
    fields,
    ...(recordId === undefined ? {} : { record_id: recordId }),
  };

  return contextRequest<Record<string, unknown> | null>(
    contextId,
    `characters.${resource}.${operation}`,
    payload,
  );
}

export function castCharacterSpell(
  contextId: number,
  characterId: number,
  spellId: number,
  slot?: string,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.spells.cast", {
    character_id: characterId,
    spell_id: spellId,
    ...(slot === undefined ? {} : { slot }),
  });
}

export function restCharacter(
  contextId: number,
  characterId: number,
  kind: "short" | "long",
  currentHp?: number,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.rest", {
    character_id: characterId,
    kind,
    ...(currentHp === undefined ? {} : { current_hp: currentHp }),
  });
}

export function setCharacterInspiration(
  contextId: number,
  characterId: number,
  available: boolean,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.inspiration.set", {
    character_id: characterId,
    available,
  });
}

export function setCharacterCondition(
  contextId: number,
  characterId: number,
  condition: ConditionMutation,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.conditions.set", {
    character_id: characterId,
    ...condition,
  });
}

export function removeCharacterCondition(
  contextId: number,
  characterId: number,
  conditionId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.conditions.remove", {
    character_id: characterId,
    condition_id: conditionId,
  });
}

export function updateEncounterCombatant(
  contextId: number,
  combatantId: number,
  fields: Partial<
    Pick<EncounterCombatant, "name" | "initiative" | "current_hp" | "max_hp">
  >,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.combatants.update", {
    combatant_id: combatantId,
    ...fields,
  });
}

export function reorderEncounterCombatants(
  contextId: number,
  combatantIds: number[],
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.combatants.reorder", {
    combatant_ids: combatantIds,
  });
}

export function setCurrentEncounterCombatant(
  contextId: number,
  combatantId: number | null,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.current.set", {
    combatant_id: combatantId,
  });
}

export function rollPlayerInitiative(contextId: number, roll: number): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.initiative.roll", {
    roll,
  });
}

export function chooseInitiativeTie(
  contextId: number,
  combatantId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.initiative.tie.choose", {
    combatant_id: combatantId,
  });
}

export function endPlayerTurn(contextId: number): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.turn.end");
}

export function startEncounter(contextId: number): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.start");
}

export function endEncounter(contextId: number): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.end");
}

export function addCharacterToEncounter(
  contextId: number,
  characterId: number,
  initiative: number,
): Promise<void> {
  return contextRequest<void>(
    contextId,
    "campaign.encounter.combatants.add_character",
    {
      character_id: characterId,
      initiative,
    },
  );
}

export function addEncounterCombatant(
  contextId: number,
  combatant: EncounterCombatantInput,
): Promise<void> {
  return contextRequest<void>(
    contextId,
    "campaign.encounter.combatants.add",
    combatant,
  );
}

export function removeEncounterCombatant(
  contextId: number,
  combatantId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.combatants.remove", {
    combatant_id: combatantId,
  });
}

export function searchCompendiumEntries(
  contextId: number,
  kind: string,
  query = "",
): Promise<CompendiumSearchEntry[]> {
  return contextRequest<CompendiumSearchEntry[]>(contextId, "compendium.search", {
    kind,
    query,
  });
}

export function setCombatantCondition(
  contextId: number,
  combatantId: number,
  condition: ConditionMutation,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.conditions.set", {
    combatant_id: combatantId,
    ...condition,
  });
}

export function removeCombatantCondition(
  contextId: number,
  combatantId: number,
  conditionId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.conditions.remove", {
    combatant_id: combatantId,
    condition_id: conditionId,
  });
}

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
export function getBuilderDefinition(contextId: number): Promise<BuilderDefinition> {
  return contextRequest<BuilderDefinition>(contextId, "characters.builder.definition");
}

export function getBuilderEntry(
  contextId: number,
  entryId: number,
): Promise<BuilderEntry & { kind: "race" | "class" | "background" }> {
  return contextRequest<BuilderEntry & { kind: "race" | "class" | "background" }>(
    contextId,
    "characters.builder.entry.get",
    { entry_id: entryId },
  );
}

export function getCharacterBuilder(
  contextId: number,
  characterId: number,
): Promise<Record<string, unknown>> {
  return contextRequest<Record<string, unknown>>(contextId, "characters.builder.get", {
    character_id: characterId,
  });
}
export function saveCharacterBuilder(
  contextId: number,
  characterId: number,
  payload: Record<string, unknown>,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.builder.save", {
    character_id: characterId,
    ...payload,
  });
}
export function completeCharacterBuilder(
  contextId: number,
  characterId: number,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.builder.complete", {
    character_id: characterId,
  });
}

export type LevelUpDefinition = {
  character: Character;
  level: number;
  preferred_class_ids: number[];
  classes: Array<
    Pick<BuilderEntry, "id" | "name" | "source" | "source_book" | "identifier">
  >;
};
export type LevelUpSubclass = {
  identifier: string;
  name: string;
  source: string;
  level: number;
};

export type LevelUpClass = {
  id: number;
  name: string;
  source: string;
  source_book: string;
  class_level: number;
  hit_die: number;
  average_hp: number;
  subclass_required: boolean;
  subclasses: LevelUpSubclass[];
};

export type LevelUpGain = {
  name: string;
  identifier: string;
  description: string;
};

export type LevelUpChoiceOption = LevelUpGain;

export type LevelUpChoice = {
  identifier: string;
  name: string;
  amount: number;
  options: LevelUpChoiceOption[];
};

export type LevelUpRules = {
  class: LevelUpClass;
  gains: LevelUpGain[];
  ability_score_improvement: boolean;
  choices: LevelUpChoice[];
};
export type LevelUpPreview = {
  rules: LevelUpRules;
  before: Character["sheet"];
  after: Character["sheet"];
};
export function getLevelUpDefinition(
  contextId: number,
  characterId: number,
): Promise<LevelUpDefinition> {
  return contextRequest<LevelUpDefinition>(
    contextId,
    "characters.level_up.definition",
    {
      character_id: characterId,
    },
  );
}
export function getLevelUpClass(
  contextId: number,
  characterId: number,
  classEntryId: number,
): Promise<LevelUpRules> {
  return contextRequest<LevelUpRules>(contextId, "characters.level_up.class.get", {
    character_id: characterId,
    class_entry_id: classEntryId,
  });
}
export function previewLevelUp(
  contextId: number,
  characterId: number,
  payload: {
    class_entry_id: number;
    hp_increase?: number;
    ability_adjustments?: Record<string, number>;
  },
): Promise<LevelUpPreview> {
  return contextRequest<LevelUpPreview>(contextId, "characters.level_up.preview", {
    character_id: characterId,
    ...payload,
  });
}
export type LevelUpFeat = {
  id: number;
  name: string;
  source: string;
  source_book: string;
};
export function getLevelUpFeats(
  contextId: number,
  characterId: number,
  query = "",
): Promise<LevelUpFeat[]> {
  return contextRequest<LevelUpFeat[]>(contextId, "characters.level_up.feats", {
    character_id: characterId,
    query,
  });
}
export function completeLevelUp(
  contextId: number,
  characterId: number,
  payload: Record<string, unknown>,
): Promise<Character> {
  return contextRequest<Character>(contextId, "characters.level_up.complete", {
    character_id: characterId,
    ...payload,
  });
}
