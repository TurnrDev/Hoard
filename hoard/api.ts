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

export type DiceCloudProfile = {
  unavailable?: boolean;
  error?: string;
  id: string;
  source_url: string;
  fetched_at: string;
  stale: boolean;
  name: string;
  image_url: string | null;
  details: Record<string, string>;
  stats: Record<string, string | number | null>;
  abilities: Record<string, string | number | null>;
  saves: Record<string, DiceCloudSave>;
  skills: Array<DiceCloudSkill>;
  resources: Array<DiceCloudEntry>;
  equipment: Array<DiceCloudEntry>;
  spells: Array<DiceCloudEntry>;
  features: Array<DiceCloudEntry>;
  currency: Record<string, number | string>;
};

export type DiceCloudSkill = {
  key: string;
  name: string;
  ability: string;
  value: string | number | null;
  proficiency: number | null;
  order: number;
};

export type DiceCloudSave = {
  value: string | number | null;
  proficiency: number | null;
};

export type DiceCloudEntry = {
  name: string;
  description: string;
  type: string;
  value: string | number | null;
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
  is_player_character: boolean;
  is_active: boolean;
  is_connected: boolean;
  dicecloud_creature_id: string | null;
  current_hp: number | null;
  max_hp: number | null;
  profile: DiceCloudProfile | null;
  race: string;
  class: string;
};

export type EncounterCombatant = {
  id: number;
  character_id: number | null;
  is_player_character: boolean;
  name: string;
  portrait_url: string | null;
  initiative: number;
  initiative_position: number;
  initiative_roll: number | null;
  initiative_modifier: number;
  can_roll_initiative: boolean;
  can_end_turn: boolean;
  tie_options: Array<{
    combatant_id: number;
    name: string;
    vote_count: number;
  }>;
  tie_choice_id: number | null;
  tie_votes_cast: number;
  tie_votes_required: number;
  tie_winner_id: number | null;
  tie_resolution: "agreement" | "random" | null;
  current_hp: number | null;
  max_hp: number | null;
  health_percentage: number | null;
  show_hp_numbers: boolean;
};

export type Encounter = {
  id: number;
  started_at: string;
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

export type PartyExperienceAward = {
  id: number;
  amount: number;
  recipient_count: number;
  awarded_per_player: number;
  discarded_amount: number;
  reason: string;
  description: string;
  occurred_at: string;
  campaign_date: string | null;
  actor: string | null;
};

export type Campaign = CampaignSummary & {
  active_context_id: number;
  shared_experience: number;
  experience_recipient_count: number;
  level: number;
  eligible_level: number;
  calendar: CampaignCalendar;
  party_money: Record<string, number | string>;
  members: CampaignMember[];
  characters: Character[];
  invitations: CampaignInvitation[];
  party_experience_awards: PartyExperienceAward[];
  encounter: Encounter | null;
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

export function linkDiceCloudCharacter(
  contextId: number,
  characterId: number,
  creature: string,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.dicecloud.link", {
    character_id: characterId,
    creature,
  });
}

export function unlinkDiceCloudCharacter(
  contextId: number,
  characterId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.dicecloud.unlink", {
    character_id: characterId,
  });
}

export function setCharacterActive(
  contextId: number,
  characterId: number,
  isActive: boolean,
): Promise<void> {
  return contextRequest<void>(contextId, "characters.active.set", {
    character_id: characterId,
    is_active: isActive,
  });
}

export function updateEncounterCombatant(
  contextId: number,
  combatantId: number,
  fields: {
    name?: string;
    initiative?: number;
    current_hp?: number;
    max_hp?: number;
  },
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
  initiative = 0,
): Promise<void> {
  return contextRequest<void>(
    contextId,
    "campaign.encounter.combatants.add_character",
    { character_id: characterId, initiative },
  );
}

export function addEncounterCombatant(
  contextId: number,
  payload: {
    name: string;
    initiative?: number;
    current_hp?: number;
    max_hp?: number;
  },
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.combatants.add", payload);
}

export function removeEncounterCombatant(
  contextId: number,
  combatantId: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.encounter.combatants.remove", {
    combatant_id: combatantId,
  });
}

export function createSharedXpAward(
  contextId: number,
  payload: { amount: number; description?: string },
): Promise<void> {
  return contextRequest<void>(contextId, "experience.shared_awards.create", payload);
}

export function setExperienceRecipientCount(
  contextId: number,
  experienceRecipientCount: number,
): Promise<void> {
  return contextRequest<void>(contextId, "campaign.experience.recipients.set", {
    experience_recipient_count: experienceRecipientCount,
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
