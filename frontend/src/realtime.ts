import { ref, watch } from "vue";

let socket: WebSocket | undefined;
let campaignId: number | undefined;
let reconnectTimer: number | undefined;
let shouldReconnect = false;
const SOCKET_CONNECT_TIMEOUT_MS = 5_000;
const SOCKET_CONNECT_POLL_MS = 50;
const REQUEST_TIMEOUT_MS = 10_000;
const IMPORT_REQUEST_TIMEOUT_MS = 120_000;
export const campaignRefreshRevision = ref(0);
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
const pendingRequests = new Map<
  string,
  {
    resolve: (data: unknown) => void;
    reject: (error: Error) => void;
    timeout: number;
  }
>();

function socketUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

function notify(id: number): void {
  window.dispatchEvent(new CustomEvent("hoard:campaign-changed", { detail: id }));
}

function open(): void {
  if (!campaignId) return;
  socket = new WebSocket(socketUrl(`/ws/contexts/${campaignId}/`));
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data) as {
      type?: string;
      request_id?: string;
      data?: unknown;
      detail?: string;
    };
    if (
      (message.type === "response" || message.type === "response.error") &&
      message.request_id
    ) {
      const pending = pendingRequests.get(message.request_id);
      if (pending) {
        window.clearTimeout(pending.timeout);
        pendingRequests.delete(message.request_id);
        if (message.type === "response.error") {
          pending.reject(new Error(message.detail ?? "Campaign request failed."));
        } else {
          pending.resolve(message.data);
        }
      }
      return;
    }
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
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const connection = await readySocket();
  const requestId = crypto.randomUUID();
  return new Promise<T>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`The ${type} campaign request timed out.`));
    }, timeoutMs);
    pendingRequests.set(requestId, {
      resolve: (data) => resolve(data as T),
      reject,
      timeout,
    });
    connection.send(JSON.stringify({ type, request_id: requestId, ...payload }));
  });
}

export const campaignImportRequest = <T>(
  type: string,
  payload: Record<string, unknown> = {},
) => campaignRequest<T>(type, payload, IMPORT_REQUEST_TIMEOUT_MS);

async function oneShotRequest<T>(
  path: string,
  type: string,
  payload: Record<string, unknown> = {},
): Promise<T> {
  const connection = new WebSocket(socketUrl(path));
  const requestId = crypto.randomUUID();
  return new Promise<T>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      connection.close();
      reject(new Error("The WebSocket request timed out."));
    }, REQUEST_TIMEOUT_MS);
    connection.onerror = () => {
      window.clearTimeout(timeout);
      reject(new Error("Could not connect to the server."));
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
      window.clearTimeout(timeout);
      connection.close();
      if (message.type === "response.error") {
        reject(
          new Error(
            typeof message.detail === "string"
              ? message.detail
              : JSON.stringify(message.detail),
          ),
        );
      } else {
        resolve(message.data as T);
      }
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
  const connection = await readySocket();
  connection.send(
    JSON.stringify({
      type: "compendium.repositories.import",
      repository_id: payload.repositoryId,
      ref: payload.ref ?? "",
    }),
  );
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
    window.clearTimeout(pending.timeout);
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

export function useCampaignRefresh(refresh: () => void | Promise<void>): void {
  watch(campaignRefreshRevision, () => void refresh());
}
