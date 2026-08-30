import { ref, watch } from "vue";

let socket: WebSocket | undefined;
let campaignId: number | undefined;
let reconnectTimer: number | undefined;
let shouldReconnect = false;
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
export type RepositoryImportEvent = {
  type:
    | "repository.import.started"
    | "repository.import.progress"
    | "repository.import.finished"
    | "repository.import.error";
  job_id?: string;
  detail?: string;
  stage?: string;
  message?: string;
  current?: number | null;
  total?: number | null;
  heartbeat?: boolean;
};
const repositoryImportListeners = new Set<(event: RepositoryImportEvent) => void>();
const domainEventListeners = new Set<(event: DomainEvent) => void>();
const reconnectListeners = new Set<() => void>();
const queryOperations = new Set([
  "campaign.get",
  "campaign.calendar.get",
  "campaign.members.list",
  "campaign.invites.list",
  "campaign.level.status",
  "characters.list",
  "characters.get",
  "characters.builder.definition",
  "characters.builder.entry.get",
  "characters.builder.get",
  "characters.level_up.definition",
  "characters.level_up.class.get",
  "characters.level_up.preview",
  "characters.level_up.feats",
  "characters.imports.cah.preview",
  "transactions.list",
  "compendium.items.list",
  "compendium.search",
  "compendium.sources.list",
  "compendium.repositories.list",
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

function notify(id: number): void {
  window.dispatchEvent(new CustomEvent("hoard:campaign-changed", { detail: id }));
}

function uuid7(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let timestamp = Date.now();
  for (let index = 5; index >= 0; index -= 1) {
    bytes[index] = timestamp & 0xff;
    timestamp = Math.floor(timestamp / 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x70;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
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
  if (!campaignId) return;
  socket = new WebSocket(socketUrl(`/ws/contexts/${campaignId}/`));
  socket.onopen = () => {
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
        if (pending.isCommand) pendingCommandCount.value -= 1;
        if (message.type === "query.error" || message.type === "command.error") {
          pending.reject(requestError(message));
        } else {
          pending.resolve(message.data);
        }
      }
      return;
    }
    domainEventListeners.forEach((listener) => listener(message as DomainEvent));
    if (message.type === "campaign.changed" && campaignId) notify(campaignId);
    if (message.type?.startsWith("repository.import.")) {
      repositoryImportListeners.forEach((listener) =>
        listener(message as RepositoryImportEvent),
      );
    }
  };
  socket.onclose = () => {
    socket = undefined;
    rejectPendingRequests("The campaign connection closed.");
    if (shouldReconnect) reconnectTimer = window.setTimeout(open, 1000);
  };
}

export function connectCampaignRealtime(id: number): void {
  if (campaignId === id && socket) return;
  disconnectCampaignRealtime();
  campaignId = id;
  shouldReconnect = true;
  open();
}

export async function ensureCampaignRealtime(id: number): Promise<WebSocket> {
  if (campaignId !== id || socket?.readyState === WebSocket.CLOSED) {
    connectCampaignRealtime(id);
  }
  return readySocket();
}

export function disconnectCampaignRealtime(): void {
  shouldReconnect = false;
  campaignId = undefined;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  reconnectTimer = undefined;
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
    if (isCommand) pendingCommandCount.value += 1;
    pendingRequests.set(requestId, {
      resolve: (data) => resolve(data as T),
      reject,
      isCommand,
    });
    connection.send(JSON.stringify({ type, request_id: requestId, ...payload }));
  });
}

export const campaignImportRequest = <T>(
  type: string,
  payload: Record<string, unknown> = {},
) => campaignRequest<T>(type, payload);

async function oneShotRequest<T>(
  path: string,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const connection = new WebSocket(socketUrl(path));
  const requestId = uuid7();
  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const rejectOnce = (error: Error) => {
      if (settled) return;
      settled = true;
      reject(error);
    };
    const resolveOnce = (data: T) => {
      if (settled) return;
      settled = true;
      resolve(data);
    };
    connection.onerror = () => {
      rejectOnce(new Error("Could not connect to the server."));
    };
    connection.onclose = () => {
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
      if (message.request_id !== requestId) return;
      if (message.type === "query.error" || message.type === "command.error") {
        rejectOnce(requestError(message));
      } else {
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

export async function startRepositoryImport(payload: {
  repositoryId: string;
  ref?: string;
}): Promise<void> {
  await campaignRequest("compendium.repositories.import", {
    repository_id: payload.repositoryId,
    ref: payload.ref ?? "",
  });
}

async function readySocket(): Promise<WebSocket> {
  const deadline = Date.now() + SOCKET_CONNECT_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (socket?.readyState === WebSocket.OPEN) return socket;
    if (!campaignId || !shouldReconnect) break;
    await new Promise<void>((resolve) => {
      window.setTimeout(resolve, SOCKET_CONNECT_POLL_MS);
    });
  }
  throw new Error("Could not connect to the campaign. Please try again.");
}

function rejectPendingRequests(detail: string): void {
  for (const pending of pendingRequests.values()) {
    if (pending.isCommand) pendingCommandCount.value -= 1;
    pending.reject(new Error(detail));
  }
  pendingRequests.clear();
}

export function subscribeRepositoryImport(
  listener: (event: RepositoryImportEvent) => void,
): () => void {
  repositoryImportListeners.add(listener);
  return () => repositoryImportListeners.delete(listener);
}

export function subscribeCampaignChanges(id: number, listener: () => void): () => void {
  const handler = (event: Event) => {
    if ((event as CustomEvent<number>).detail === id) listener();
  };
  window.addEventListener("hoard:campaign-changed", handler);
  return () => window.removeEventListener("hoard:campaign-changed", handler);
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
