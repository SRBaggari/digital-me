import { describe, expect, it, vi } from "vitest";

import { SpeechQueue, type AudioBackend, type SpeechClip } from "../../../src/audio/speechQueue";

/** Backend where decoding is instant and each clip "plays" until the test ends it. */
function instantBackend() {
  const ends: (() => void)[] = [];
  const stops = vi.fn();
  const backend: AudioBackend<string> = {
    unlock: vi.fn(),
    decode: async (wav) => String(wav.byteLength),
    play: (_buffer, onEnded) => {
      ends.push(onEnded);
      return { stop: stops };
    },
    level: () => 0.3,
  };
  return { backend, ends, stops };
}

const clip = (text: string): SpeechClip => ({ index: 0, text, emotion: "happy", words: [], data: btoa(text) });
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("SpeechQueue", () => {
  it("plays clips one after another and reports each start, then idle", async () => {
    const { backend, ends } = instantBackend();
    const started: string[] = [];
    const onIdle = vi.fn();
    const queue = new SpeechQueue(backend, { onClipStart: (c) => started.push(c.text), onIdle });
    queue.enqueue(clip("one"));
    queue.enqueue(clip("two"));
    await flush();
    expect(started).toEqual(["one"]);
    expect(queue.playing).toBe(true);
    ends[0]();
    await flush();
    expect(started).toEqual(["one", "two"]);
    ends[1]();
    await flush();
    expect(onIdle).toHaveBeenCalledTimes(1);
    expect(queue.playing).toBe(false);
  });

  it("stop() silences the current clip, drops the rest and reports idle", async () => {
    const { backend, stops } = instantBackend();
    const started: string[] = [];
    const onIdle = vi.fn();
    const queue = new SpeechQueue(backend, { onClipStart: (c) => started.push(c.text), onIdle });
    queue.enqueue(clip("one"));
    queue.enqueue(clip("two"));
    await flush();
    queue.stop();
    await flush();
    expect(stops).toHaveBeenCalled();
    expect(onIdle).toHaveBeenCalledTimes(1);
    expect(started).toEqual(["one"]);
  });

  it("stop() when idle is harmless", () => {
    const onIdle = vi.fn();
    new SpeechQueue(instantBackend().backend, { onIdle }).stop();
    expect(onIdle).not.toHaveBeenCalled();
  });

  it("can play again after being stopped", async () => {
    const { backend } = instantBackend();
    const started: string[] = [];
    const queue = new SpeechQueue(backend, { onClipStart: (c) => started.push(c.text) });
    queue.enqueue(clip("one"));
    await flush();
    queue.stop();
    queue.enqueue(clip("again"));
    await flush();
    expect(started).toEqual(["one", "again"]);
  });

  it("unlock() is passed to the audio backend", () => {
    const { backend } = instantBackend();
    new SpeechQueue(backend).unlock();
    expect(backend.unlock).toHaveBeenCalled();
  });
});
