import { afterEach, describe, expect, it } from "vitest";
import {
  markConnectionAvailable,
  markConnectionUnavailable,
  serverIsReconnecting,
  type ConnectionSource,
} from "./connection";

const connectionSources: ConnectionSource[] = ["browser", "campaign", "http", "user"];

describe("server connection state", () => {
  afterEach(() => {
    for (const source of connectionSources) {
      markConnectionAvailable(source);
    }
  });

  it("remains reconnecting until every unavailable connection recovers", () => {
    markConnectionUnavailable("http");
    markConnectionUnavailable("campaign");

    expect(serverIsReconnecting.value).toBe(true);

    markConnectionAvailable("http");

    expect(serverIsReconnecting.value).toBe(true);

    markConnectionAvailable("campaign");

    expect(serverIsReconnecting.value).toBe(false);
  });
});
