import axios from "axios";
import { markConnectionAvailable, markConnectionUnavailable } from "./connection";
import {
  campaignRequest,
  ensureCampaignRealtime,
  inviteRequest,
  userRequest,
} from "./realtime";

export type User = {
  id: number;
  username: string;
};

export type Calculation = {
  value: number;
  base: number;
  formula?: string;
  numeric_formula?: string;
  components: Array<{
    label: string;
    value: number;
    formula?: string;
    source?: string;
  }>;
};

export type CharacterSheet = {
  level: number;
  rolled_hit_points: number;
  hp_ability: string;
  hp_adjustment: number;
  initiative_adjustment: number;
  proficiency_bonus_adjustment: number;
  max_hp: number;
  hp_calculation: Calculation;
  current_hp: number;
  temporary_hp: number;
  initiative: Calculation;
  proficiency_bonus: number;
  proficiency_bonus_calculation: Calculation;
  jack_of_all_trades: boolean;
  remarkable_athlete: boolean;
  abilities: Record<
    string,
    {
      score: number;
      raw: number;
      ancestry_bonus: number;
      background_bonus: number;
      score_adjustment: number;
      modifier: number;
      check_bonus: number;
      check_formula: Calculation;
      formula: Calculation;
    }
  >;
  saves: Record<
    string,
    { proficiency: string; adjustment: number; bonus: number; formula: Calculation }
  >;
  skills: Record<
    string,
    {
      ability: string;
      proficiency: string;
      adjustment: number;
      bonus: number;
      formula: Calculation;
    }
  >;
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

export type Character = {
  id: number;
  context_id: number | null;
  name: string;
  portrait_url: string | null;
  kind: "pc" | "npc";
  is_player_character: boolean;
  is_active: boolean;
  race: string;
  class: string;
  experience: number;
  sheet: CharacterSheet;
  money: Record<string, number | string>;
};

export type EncounterCombatant = {
  id: number;
  character_id: number | null;
  name: string;
  portrait_url: string | null;
  initiative: number;
  initiative_roll: number | null;
  initiative_modifier: number;
  position: number;
  current_hp: number | null;
  max_hp: number | null;
  health_percentage: number | null;
  show_hp_numbers: boolean;
};

export type Encounter = {
  id: number;
  current_combatant_id: number | null;
  combatants: EncounterCombatant[];
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

export type Campaign = CampaignSummary & {
  shared_experience: number;
  level: number;
  eligible_level: number;
  calendar: CampaignCalendar;
  party_money: Record<string, number | string>;
  members: CampaignMember[];
  characters: Character[];
  invitations: CampaignInvitation[];
  encounter: Encounter | null;
};

export type LedgerEntry = {
  account_id: number;
  account_name: string;
  is_system_account: boolean;
  amount: number;
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
  changes?: Record<string, { before: unknown; after: unknown }>;
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

export type InviteDetails = {
  campaign_name: string;
  expires_at: string;
  authenticated: boolean;
  username: string | null;
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

async function contextRequest<T>(
  contextId: number,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  await ensureCampaignRealtime(contextId);

  return campaignRequest<T>(type, payload);
}

export function isUnauthenticatedError(error: unknown): boolean {
  if (!(error instanceof Error) || !axios.isAxiosError(error.cause)) {
    return false;
  }

  return error.cause.response?.status === 401;
}

export async function initialiseCsrf(): Promise<void> {
  const response = await request<{ csrfToken: string }>("/api/auth/csrf/");

  csrfToken = getCookie("csrftoken") || response.csrfToken;
}

export function getSession(): Promise<User> {
  return request<User>("/api/auth/session/");
}

export function login(username: string, password: string): Promise<User> {
  return request<User>("/api/auth/session/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
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

    campaigns.set(context.campaign_id, {
      id: context.campaign_id,
      name: context.campaign_name,
      is_game_master: Boolean(previous?.is_game_master || context.kind === "gm"),
    });
  }

  return [...campaigns.values()];
}

export async function getCampaign(contextId: number): Promise<Campaign> {
  await ensureCampaignRealtime(contextId);

  return campaignRequest<Campaign>("campaign.get");
}

export function getCalendar(contextId: number): Promise<CampaignCalendar> {
  return contextRequest<CampaignCalendar>(contextId, "campaign.calendar.get");
}

export function adjustCalendar(contextId: number, amount: -1 | 1): Promise<void> {
  return contextRequest<void>(contextId, "campaign.calendar.adjust", { amount });
}

export function removeMember(contextId: number, memberId: number): Promise<void> {
  return contextRequest<void>(contextId, "campaign.members.deactivate", {
    member_id: memberId,
  });
}

export function getCharacters(contextId: number): Promise<Character[]> {
  return contextRequest<Character[]>(contextId, "characters.list");
}

export async function getMyCharacters(contextId: number): Promise<Character[]> {
  const characters = await getCharacters(contextId);

  return characters.filter((character) => character.context_id === contextId);
}

export function getMembers(contextId: number): Promise<CampaignMember[]> {
  return contextRequest<CampaignMember[]>(contextId, "campaign.members.list");
}

export function createCharacter(
  contextId: number,
  payload: {
    name: string;
    race: string;
    character_class: string;
    is_npc?: boolean;
  },
): Promise<void> {
  return contextRequest<void>(contextId, "characters.create", {
    fields: payload,
  });
}

export function archiveCharacter(
  contextId: number,
  characterId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.archive", {
    character_id: characterId,
  });
}

export function updateCharacter(
  contextId: number,
  characterId: number,
  payload: Record<string, unknown>,
): Promise<void> {
  const { class: characterClass, ...fields } = payload as {
    class?: string;
  } & Record<string, unknown>;

  return contextRequest<void>(contextId, "characters.update", {
    character_id: characterId,
    fields: { ...fields, character_class: characterClass },
  });
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
): Promise<void> {
  return contextRequest<void>(contextId, "characters.health.post", payload);
}

export function takeRest(
  contextId: number,
  characterId: number,
  kind: "short" | "long",
  regainedHp = 0,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.rest", {
    character_id: characterId,
    kind,
    regained_hp: regainedHp,
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

export function createMoneyTransfer(
  contextId: number,
  payload: MoneyTransferInput,
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    contextId,
    "money.transfers.create",
    payload,
  );
}

export function createMoneyExchange(
  contextId: number,
  payload: MoneyExchangeInput,
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    contextId,
    "money.exchanges.create",
    payload,
  );
}

export function createSharedXpAward(
  contextId: number,
  payload: { amount: number; description?: string },
): Promise<LedgerTransaction> {
  return contextRequest<LedgerTransaction>(
    contextId,
    "experience.shared_awards.create",
    payload,
  );
}

export function getTransactions(
  contextId: number,
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

  return contextRequest(contextId, "transactions.list", payload);
}

export function reverseTransaction(
  contextId: number,
  transaction: LedgerTransaction,
): Promise<void> {
  return contextRequest<void>(contextId, "transactions.reverse", {
    ledger: transaction.ledger,
    transaction_id: transaction.id,
  });
}

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

export function inspectInvite(token: string): Promise<InviteDetails> {
  return inviteRequest<InviteDetails>(token, "invite.inspect");
}

export function acceptInvite(
  token: string,
): Promise<{ context_id: number; character_id: number }> {
  return inviteRequest(token, "invite.accept");
}

export function registerAndAcceptInvite(
  token: string,
  payload: { username: string; email: string; password: string },
): Promise<{
  context_id: number;
  character_id: number;
  username: string;
}> {
  return inviteRequest(token, "invite.register_and_accept", payload);
}
