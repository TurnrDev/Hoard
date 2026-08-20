import { ref, watch } from "vue";

let socket: WebSocket | undefined;
let campaignId: number | undefined;
let reconnectTimer: number | undefined;
let shouldReconnect = false;
export const campaignRefreshRevision = ref(0);

function socketUrl(id: number): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/campaigns/${id}/`;
}

function notify(id: number): void {
  window.dispatchEvent(new CustomEvent("hoard:campaign-changed", { detail: id }));
}

function open(): void {
  if (!campaignId) return;
  socket = new WebSocket(socketUrl(campaignId));
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data) as { type?: string };
    if (message.type === "campaign.changed" && campaignId) notify(campaignId);
  };
  socket.onclose = () => {
    socket = undefined;
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

export function disconnectCampaignRealtime(): void {
  shouldReconnect = false;
  campaignId = undefined;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  reconnectTimer = undefined;
  socket?.close();
  socket = undefined;
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
