import { afterEach, describe, expect, it, vi } from "vitest";
import { alertCurrentTurn } from "./turnAlert";

describe("current turn alert", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attempts the tone even when vibration succeeds", () => {
    const vibrate = vi.fn().mockReturnValue(true);
    const start = vi.fn();
    const stop = vi.fn();
    const close = vi.fn().mockResolvedValue(undefined);

    class TestAudioContext {
      currentTime = 0;
      destination = {};

      createOscillator() {
        return {
          type: "sine",
          frequency: { setValueAtTime: vi.fn() },
          connect: vi.fn(),
          start,
          stop,
          addEventListener: (_event: string, handler: () => void) => handler(),
        };
      }

      createGain() {
        return {
          gain: {
            setValueAtTime: vi.fn(),
            exponentialRampToValueAtTime: vi.fn(),
          },
          connect: vi.fn(),
        };
      }

      resume() {
        return Promise.resolve();
      }

      close() {
        return close();
      }
    }

    vi.stubGlobal("navigator", { vibrate });
    vi.stubGlobal("window", { AudioContext: TestAudioContext });

    alertCurrentTurn();

    expect(vibrate).toHaveBeenCalledWith([140, 70, 140]);
    expect(start).toHaveBeenCalledOnce();
    expect(stop).toHaveBeenCalledOnce();
  });
});
