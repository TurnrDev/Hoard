import { afterEach, describe, expect, it, vi } from "vitest";

const { SocketDouble } = vi.hoisted(() => {
  class SocketDouble {
    static instances: SocketDouble[] = [];

    readonly readyState = 1;
    onopen: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;
    readonly send = vi.fn();

    constructor() {
      SocketDouble.instances.push(this);
    }

    close(): void {
      this.onclose?.();
    }

    deliver(message: Record<string, unknown>): void {
      this.onmessage?.({ data: JSON.stringify(message) });
    }
  }

  return { SocketDouble };
});

vi.mock("reconnecting-websocket", () => ({ default: SocketDouble }));
vi.mock("uuid", () => ({ v7: () => "0197d6c5-6a24-7000-8000-000000000000" }));

import {
  campaignRequest,
  connectCampaignRealtime,
  disconnectCampaignRealtime,
  pendingCommandCount,
  subscribeDomainEvents,
} from "./realtime";

function activeSocket(): InstanceType<typeof SocketDouble> {
  const socket = SocketDouble.instances.at(-1);
  if (!socket) {
    throw new Error("Expected a campaign socket.");
  }

  return socket;
}

describe("campaign realtime transport", () => {
  afterEach(() => {
    disconnectCampaignRealtime();
    SocketDouble.instances = [];
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("correlates queries and dispatches server domain events", async () => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "example.test" },
      setTimeout,
    });
    vi.stubGlobal("WebSocket", { OPEN: 1, CLOSED: 3 });
    const listener = vi.fn();
    const unsubscribe = subscribeDomainEvents(listener);
    connectCampaignRealtime(7);
    const socket = activeSocket();

    const result = campaignRequest<{ year: number }>("campaign.calendar.get");
    await vi.waitFor(() => expect(socket.send).toHaveBeenCalledOnce());
    const sent = JSON.parse(socket.send.mock.calls[0][0]) as Record<string, unknown>;
    socket.deliver({
      type: "query.result",
      request_id: sent.request_id,
      data: { year: 82 },
    });
    socket.deliver({
      type: "campaign.calendar_changed",
      calendar: { year: 82 },
    });

    await expect(result).resolves.toEqual({ year: 82 });
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({ type: "campaign.calendar_changed" }),
    );
    unsubscribe();
  });

  it("tracks a pending command until its acknowledgement arrives", async () => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "example.test" },
      setTimeout,
    });
    vi.stubGlobal("WebSocket", { OPEN: 1, CLOSED: 3 });
    connectCampaignRealtime(7);
    const socket = activeSocket();

    const result = campaignRequest<void>("campaign.calendar.adjust", { amount: 1 });
    await vi.waitFor(() => expect(socket.send).toHaveBeenCalledOnce());
    const sent = JSON.parse(socket.send.mock.calls[0][0]) as Record<string, unknown>;
    expect(pendingCommandCount.value).toBe(1);
    socket.deliver({ type: "command.ack", request_id: sent.request_id });

    await expect(result).resolves.toBeUndefined();
    expect(pendingCommandCount.value).toBe(0);
  });
});
