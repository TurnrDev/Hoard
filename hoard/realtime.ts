import { ref, watch } from "vue";
import ReconnectingWebSocket from "reconnecting-websocket";
import { v7 as uuid7 } from "uuid";
import { markConnectionAvailable, markConnectionUnavailable } from "./connection";

let socket: ReconnectingWebSocket | undefined;
let campaignId: number | undefined;
let presenceHeartbeatTimer: number | undefined;
const SOCKET_CONNECT_TIMEOUT_MS = 5_000;
const SOCKET_CONNECT_POLL_MS = 50;
export const campaignRefreshRevision = ref(0);
export const pendingCommandCount = ref(0);
export class CommandError extends Error {
  readonly code: string;
  readonly fieldErrors: Record<string, unknown>;

  constructor(
    message: string,
    code: string,
    fieldErrors: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "CommandError";
    this.code = code;
    this.fieldErrors = fieldErrors;
  }
}
export type DomainEvent = {
  type: string;
  request_id?: string;
  [key: string]: unknown;
};
export type CampaignCalendarEventData = {
  era_abbreviation: string;
  era_name: string;
  year: number;
  day: number;
};
const domainEventListeners = new Set<(event: DomainEvent) => void>();
const reconnectListeners = new Set<() => void>();
const queryOperations = new Set([
  "campaign.get",
  "campaign.calendar.get",
  "campaign.members.list",
  "campaign.invites.list",
  "characters.list",
  "characters.get",
  "transactions.list",
]);
const pendingRequests = new Map<
  string,
  {
    resolve: (data: unknown) => void;
    reject: (error: Error) => void;
    isCommand: boolean;
  }
>();

function socketUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

function requestError(message: {
  type?: string;
  detail?: unknown;
  code?: unknown;
  field_errors?: unknown;
}): Error {
  const detail =
    typeof message.detail === "string"
      ? message.detail
      : message.detail === undefined
        ? "Campaign request failed."
        : JSON.stringify(message.detail);
  if (message.type === "command.error") {
    return new CommandError(
      detail,
      typeof message.code === "string" ? message.code : "command_failed",
      message.field_errors && typeof message.field_errors === "object"
        ? (message.field_errors as Record<string, unknown>)
        : {},
    );
  }
  return new Error(detail);
}

function open(): void {
  if (!campaignId) {
    return;
  }
  const openedCampaignId = campaignId;
  socket = new ReconnectingWebSocket(socketUrl(`/ws/contexts/${campaignId}/`), [], {
    connectionTimeout: SOCKET_CONNECT_TIMEOUT_MS,
    maxReconnectionDelay: 1_000,
    minReconnectionDelay: 1_000,
    reconnectionDelayGrowFactor: 1,
  });
  socket.onopen = () => {
    markConnectionAvailable("campaign");
    startPresenceHeartbeat();
    reconnectListeners.forEach((listener) => listener());
  };
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data) as {
      type?: string;
      request_id?: string;
      data?: unknown;
      detail?: unknown;
      code?: unknown;
      field_errors?: unknown;
    };
    if (
      (message.type === "query.result" ||
        message.type === "command.ack" ||
        message.type === "query.error" ||
        message.type === "command.error") &&
      message.request_id
    ) {
      const pending = pendingRequests.get(message.request_id);
      if (pending) {
        pendingRequests.delete(message.request_id);
        if (pending.isCommand) {
          pendingCommandCount.value -= 1;
        }
        if (message.type === "query.error" || message.type === "command.error") {
          pending.reject(requestError(message));
        } else {
          pending.resolve(message.data);
        }
      }
      return;
    }
    domainEventListeners.forEach((listener) => listener(message as DomainEvent));
  };
  socket.onclose = () => {
    stopPresenceHeartbeat();
    rejectPendingRequests("The campaign connection closed.");

    if (campaignId === openedCampaignId) {
      markConnectionUnavailable("campaign");
    }
  };
}

function startPresenceHeartbeat(): void {
  stopPresenceHeartbeat();
  void campaignRequest<void>("campaign.presence.heartbeat").catch(() => undefined);
  presenceHeartbeatTimer = window.setInterval(() => {
    void campaignRequest<void>("campaign.presence.heartbeat").catch(() => undefined);
  }, 25_000);
}

function stopPresenceHeartbeat(): void {
  if (presenceHeartbeatTimer !== undefined) {
    window.clearInterval(presenceHeartbeatTimer);
    presenceHeartbeatTimer = undefined;
  }
}

export function connectCampaignRealtime(id: number): void {
  if (campaignId === id && socket) {
    return;
  }
  disconnectCampaignRealtime();
  campaignId = id;
  open();
}

export async function ensureCampaignRealtime(
  id: number,
): Promise<ReconnectingWebSocket> {
  if (campaignId !== id || socket?.readyState === WebSocket.CLOSED) {
    connectCampaignRealtime(id);
  }
  return readySocket();
}

export function disconnectCampaignRealtime(): void {
  campaignId = undefined;
  markConnectionAvailable("campaign");
  stopPresenceHeartbeat();
  socket?.close();
  socket = undefined;
  rejectPendingRequests("The campaign connection closed.");
}

export async function campaignRequest<T>(
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const connection = await readySocket();
  const requestId = uuid7();
  const isCommand = !queryOperations.has(type);
  return new Promise<T>((resolve, reject) => {
    if (isCommand) {
      pendingCommandCount.value += 1;
    }
    pendingRequests.set(requestId, {
      resolve: (data) => resolve(data as T),
      reject,
      isCommand,
    });
    connection.send(JSON.stringify({ type, request_id: requestId, ...payload }));
  });
}

async function oneShotRequest<T>(
  path: string,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const connection = new ReconnectingWebSocket(socketUrl(path), [], {
    maxRetries: 0,
  });
  const requestId = uuid7();
  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const rejectOnce = (error: Error) => {
      if (settled) {
        return;
      }
      settled = true;
      reject(error);
    };
    const resolveOnce = (data: T) => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(data);
    };
    connection.onerror = () => {
      markConnectionUnavailable("user");
      rejectOnce(new Error("Could not connect to the server."));
    };
    connection.onclose = () => {
      if (!settled) {
        markConnectionUnavailable("user");
      }

      rejectOnce(new Error("The WebSocket connection closed before completing."));
    };
    connection.onopen = () => {
      connection.send(JSON.stringify({ type, request_id: requestId, ...payload }));
    };
    connection.onmessage = (event) => {
      const message = JSON.parse(event.data) as {
        type?: string;
        request_id?: string;
        data?: unknown;
        detail?: unknown;
      };
      if (message.request_id !== requestId) {
        return;
      }
      if (message.type === "query.error" || message.type === "command.error") {
        markConnectionAvailable("user");
        rejectOnce(requestError(message));
      } else {
        markConnectionAvailable("user");
        resolveOnce(message.data as T);
      }
      connection.close();
    };
  });
}

export const userRequest = <T>(type: string, payload: Record<string, unknown> = {}) =>
  oneShotRequest<T>("/ws/user/", type, payload);

export const inviteRequest = <T>(
  token: string,
  type: string,
  payload: Record<string, unknown> = {},
) => oneShotRequest<T>(`/ws/invites/${encodeURIComponent(token)}/`, type, payload);

async function readySocket(): Promise<ReconnectingWebSocket> {
  const deadline = Date.now() + SOCKET_CONNECT_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (socket?.readyState === WebSocket.OPEN) {
      return socket;
    }
    if (!campaignId) {
      break;
    }
    await new Promise<void>((resolve) => {
      window.setTimeout(resolve, SOCKET_CONNECT_POLL_MS);
    });
  }
  throw new Error("Could not connect to the campaign. Please try again.");
}

function rejectPendingRequests(detail: string): void {
  for (const pending of pendingRequests.values()) {
    if (pending.isCommand) {
      pendingCommandCount.value -= 1;
    }
    pending.reject(new Error(detail));
  }
  pendingRequests.clear();
}

export function subscribeCampaignChanges(listener: () => void): () => void {
  return subscribeDomainEvents((event) => {
    if (event.type !== "campaign.presence_changed") {
      listener();
    }
  });
}

export function subscribeCampaignPresence(
  listener: (event: {
    context_id: number;
    connected: boolean;
    last_seen_at: string | null;
  }) => void,
): () => void {
  return subscribeDomainEvents((event) => {
    if (
      event.type === "campaign.presence_changed" &&
      typeof event.context_id === "number" &&
      typeof event.connected === "boolean" &&
      (typeof event.last_seen_at === "string" || event.last_seen_at === null)
    ) {
      listener({
        context_id: event.context_id,
        connected: event.connected,
        last_seen_at: event.last_seen_at,
      });
    }
  });
}

export function subscribeCampaignCalendar(
  listener: (calendar: CampaignCalendarEventData) => void,
): () => void {
  return subscribeDomainEvents((event) => {
    if (event.type !== "campaign.calendar_changed") {
      return;
    }

    const calendar = event.calendar;

    if (
      typeof calendar === "object" &&
      calendar !== null &&
      "era_abbreviation" in calendar &&
      typeof calendar.era_abbreviation === "string" &&
      "era_name" in calendar &&
      typeof calendar.era_name === "string" &&
      "year" in calendar &&
      typeof calendar.year === "number" &&
      "day" in calendar &&
      typeof calendar.day === "number"
    ) {
      listener({
        era_abbreviation: calendar.era_abbreviation,
        era_name: calendar.era_name,
        year: calendar.year,
        day: calendar.day,
      });
    }
  });
}

export function subscribeDomainEvents(
  listener: (event: DomainEvent) => void,
): () => void {
  domainEventListeners.add(listener);
  return () => domainEventListeners.delete(listener);
}

export function subscribeCampaignReconnect(listener: () => void): () => void {
  reconnectListeners.add(listener);
  return () => reconnectListeners.delete(listener);
}

export function useCampaignRefresh(refresh: () => void | Promise<void>): void {
  watch(campaignRefreshRevision, () => void refresh());
}
