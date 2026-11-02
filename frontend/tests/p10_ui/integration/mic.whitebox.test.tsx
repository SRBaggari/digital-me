import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useDigitalMe } from "../../../src/hooks/useDigitalMe";
import { controllableSocket, fakeMic, fakeSpeaker } from "../../helpers";

function setup() {
  const socket = controllableSocket();
  const audio = fakeSpeaker();
  const microphone = fakeMic();
  const hook = renderHook(() => useDigitalMe(socket.factory, "ws://x", audio.factory, microphone.factory));
  act(() => socket.open());
  return { socket, audio, microphone, ...hook };
}

describe("microphone wiring", () => {
  it("re-announces the open microphone after a reconnect", async () => {
    const { socket, result } = setup();
    await act(async () => result.current.toggleMic());
    socket.sent.length = 0;
    act(() => socket.drop());
    act(() => socket.open());
    expect(socket.sent).toContainEqual({ type: "mic_start" });
  });

  it("closes the microphone when the server says it cannot listen", async () => {
    const { socket, microphone, result } = setup();
    await act(async () => result.current.toggleMic());
    act(() => socket.emit({ type: "error", code: "not_available", detail: "Voice input is not available" }));
    expect(microphone.mic.stop).toHaveBeenCalled();
    expect(result.current.state.mic).toBe("off");
  });

  it("tells the server whenever Digital Me starts or stops being audible", () => {
    const { socket, audio, result } = setup();
    act(() => result.current.setVoiceEnabled(true));
    socket.sent.length = 0;
    act(() => audio.start({ index: 0, text: "x", emotion: "neutral", words: [], data: "" }));
    act(() => audio.idle());
    expect(socket.sent).toEqual([
      { type: "playback", playing: true },
      { type: "playback", playing: false },
    ]);
  });

  it("the presence follows the microphone level while listening", async () => {
    const { result } = setup();
    expect(result.current.level()).toBe(0);
    await act(async () => result.current.toggleMic());
    expect(result.current.level()).toBe(0.4);
  });

  it("frames are dropped, not queued, while disconnected", async () => {
    const { socket, microphone, result } = setup();
    await act(async () => result.current.toggleMic());
    act(() => socket.drop());
    act(() => microphone.frame());
    expect(socket.binary).toEqual([]);
  });

  it("opening the microphone also unlocks audio playback (same click)", async () => {
    const { audio, result } = setup();
    await act(async () => result.current.toggleMic());
    expect(audio.speaker.unlock).toHaveBeenCalled();
  });

  it("stopping during the permission prompt leaves the microphone closed", async () => {
    const { socket, microphone, result } = setup();
    let finishStart: () => void = () => {};
    microphone.mic.start.mockImplementationOnce(() => new Promise<void>((resolve) => (finishStart = resolve)));
    act(() => result.current.toggleMic()); // asks for permission...
    act(() => result.current.toggleMic()); // ...user clicks again before answering
    await act(async () => finishStart());
    expect(result.current.state.mic).toBe("off");
    expect(socket.sent).not.toContainEqual({ type: "mic_start" });
    expect(microphone.mic.stop).toHaveBeenCalled();
  });

  it("ignores a second start while the first is still starting", async () => {
    const { microphone, result } = setup();
    await act(async () => {
      result.current.toggleMic();
      result.current.toggleMic();
    });
    expect(microphone.mic.start).toHaveBeenCalledTimes(1);
  });
});
