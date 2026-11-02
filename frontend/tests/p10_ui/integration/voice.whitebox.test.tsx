import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useDigitalMe } from "../../../src/hooks/useDigitalMe";
import { useVoice } from "../../../src/hooks/useVoice";
import { VOICE, audioEvent, controllableSocket, fakeApi, fakeSpeaker } from "../../helpers";

describe("voice wiring", () => {
  it("useVoice updates optimistically, then adopts the server's answer", async () => {
    let release: () => void = () => {};
    const api = fakeApi({
      updateVoice: vi.fn(
        () =>
          new Promise<typeof VOICE>((resolve) => {
            release = () => resolve({ ...VOICE, settings: { ...VOICE.settings, voice: "bf_emma" } });
          }),
      ),
    });
    const { result } = renderHook(() => useVoice(api));
    await waitFor(() => expect(result.current.voice).not.toBeNull());
    act(() => {
      void result.current.update({ voice: "bf_emma" });
    });
    expect(result.current.voice?.settings.voice).toBe("bf_emma"); // before the server answered
    await act(async () => release());
    expect(result.current.voice?.settings.voice).toBe("bf_emma");
  });

  it("useVoice rolls back to the server state when saving fails", async () => {
    const api = fakeApi({ updateVoice: vi.fn(async () => Promise.reject(new Error("Unknown voice"))) });
    const { result } = renderHook(() => useVoice(api));
    await waitFor(() => expect(result.current.voice).not.toBeNull());
    await act(async () => result.current.update({ voice: "nope" }));
    expect(result.current.voice?.settings.voice).toBe("af_heart");
    expect(result.current.error).toBe("Unknown voice");
  });

  it("useVoice marks voice unavailable when the server has none", async () => {
    const { result } = renderHook(() => useVoice(fakeApi({ voice: async () => Promise.reject(new Error("404")) })));
    await waitFor(() => expect(result.current.available).toBe(false));
  });

  it("audio frames are routed to the speaker only while voice is on", () => {
    const socket = controllableSocket();
    const audio = fakeSpeaker();
    const { result } = renderHook(() => useDigitalMe(socket.factory, "ws://x", audio.factory));
    act(() => socket.open());
    act(() => socket.emit(audioEvent(0, "muted")));
    expect(audio.clips).toEqual([]);
    act(() => result.current.setVoiceEnabled(true));
    act(() => socket.emit(audioEvent(1, "spoken")));
    expect(audio.clips.map((c) => c.text)).toEqual(["spoken"]);
  });

  it("a new conversation from the server stops any playback", () => {
    const socket = controllableSocket();
    const audio = fakeSpeaker();
    renderHook(() => useDigitalMe(socket.factory, "ws://x", audio.factory));
    act(() => socket.emit({ type: "conversation", conversation_id: 5, messages: [] }));
    expect(audio.speaker.stop).toHaveBeenCalled();
  });

  it("level() follows Digital Me's voice while it plays, and is silent otherwise", () => {
    const audio = fakeSpeaker();
    const socket = controllableSocket(); // factories must be stable, as in the app
    const { result } = renderHook(() => useDigitalMe(socket.factory, "ws://x", audio.factory));
    expect(result.current.level()).toBe(0);
    act(() => result.current.setVoiceEnabled(true));
    act(() => audio.start({ index: 0, text: "x", emotion: "neutral", words: [], data: "" }));
    expect(result.current.level()).toBe(0.5);
  });
});
