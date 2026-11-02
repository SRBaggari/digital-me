import { describe, expect, it, vi } from "vitest";

import { SpeechQueue, base64ToArrayBuffer, type AudioBackend, type SpeechClip } from "../../../src/audio/speechQueue";

/** Backend whose decode and playback completion are controlled by the test. */
function controlledBackend() {
  const decodes: { resolve: (b: string) => void; reject: (e: unknown) => void }[] = [];
  const plays: { buffer: string; end: () => void; stop: ReturnType<typeof vi.fn> }[] = [];
  const backend: AudioBackend<string> = {
    unlock: vi.fn(),
    decode: () => new Promise<string>((resolve, reject) => decodes.push({ resolve, reject })),
    play: (buffer, onEnded) => {
      const stop = vi.fn();
      plays.push({ buffer, end: onEnded, stop });
      return { stop };
    },
    level: () => 0.7,
  };
  return { backend, decodes, plays };
}

const clip = (index: number): SpeechClip => ({ index, text: `s${index}`, emotion: "neutral", words: [], data: btoa("x") });
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("SpeechQueue internals", () => {
  it("decodes every clip as soon as it arrives (no gap between sentences)", () => {
    const { backend, decodes } = controlledBackend();
    const queue = new SpeechQueue(backend);
    queue.enqueue(clip(0));
    queue.enqueue(clip(1));
    expect(decodes).toHaveLength(2);
  });

  it("keeps order even if a later clip decodes first", async () => {
    const { backend, decodes, plays } = controlledBackend();
    const queue = new SpeechQueue(backend);
    queue.enqueue(clip(0));
    queue.enqueue(clip(1));
    decodes[1].resolve("b1");
    await flush();
    expect(plays).toEqual([]);
    decodes[0].resolve("b0");
    await flush();
    expect(plays.map((p) => p.buffer)).toEqual(["b0"]);
    plays[0].end();
    await flush();
    expect(plays.map((p) => p.buffer)).toEqual(["b0", "b1"]);
  });

  it("ignores a decode that finishes after stop()", async () => {
    const { backend, decodes, plays } = controlledBackend();
    const onClipStart = vi.fn();
    const queue = new SpeechQueue(backend, { onClipStart });
    queue.enqueue(clip(0));
    queue.stop();
    decodes[0].resolve("late");
    await flush();
    expect(plays).toEqual([]);
    expect(onClipStart).not.toHaveBeenCalled();
  });

  it("an ended callback from a stopped clip does not advance the new queue", async () => {
    const { backend, decodes, plays } = controlledBackend();
    const queue = new SpeechQueue(backend);
    queue.enqueue(clip(0));
    decodes[0].resolve("old");
    await flush();
    queue.stop();
    queue.enqueue(clip(1));
    queue.enqueue(clip(2));
    decodes[1].resolve("new1");
    decodes[2].resolve("new2");
    await flush();
    plays[0].end(); // stale callback from the stopped clip
    await flush();
    expect(plays.map((p) => p.buffer)).toEqual(["old", "new1"]);
  });

  it("skips clips that fail to decode and reports the error", async () => {
    const { backend, decodes, plays } = controlledBackend();
    const onError = vi.fn();
    const queue = new SpeechQueue(backend, { onError });
    queue.enqueue(clip(0));
    queue.enqueue(clip(1));
    decodes[0].reject(new Error("bad wav"));
    decodes[1].resolve("ok");
    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(plays.map((p) => p.buffer)).toEqual(["ok"]);
  });

  it("level is 0 when nothing plays", async () => {
    const { backend, decodes } = controlledBackend();
    const queue = new SpeechQueue(backend);
    expect(queue.level()).toBe(0);
    queue.enqueue(clip(0));
    decodes[0].resolve("b");
    await flush();
    expect(queue.level()).toBe(0.7);
  });

  it("base64ToArrayBuffer decodes bytes", () => {
    expect([...new Uint8Array(base64ToArrayBuffer(btoa("RIFF")))]).toEqual([82, 73, 70, 70]);
  });
});
