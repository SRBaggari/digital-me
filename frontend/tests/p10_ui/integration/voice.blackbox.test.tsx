import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { App } from "../../../src/App";
import { audioEvent, controllableSocket, dto, fakeApi, fakeSpeaker } from "../../helpers";

beforeAll(() => {
  // jsdom has no media playback
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  window.HTMLMediaElement.prototype.play = vi.fn(async () => {});
  window.HTMLMediaElement.prototype.pause = vi.fn();
});

async function start(api = fakeApi()) {
  const socket = controllableSocket();
  const audio = fakeSpeaker();
  render(<App api={api} socketFactory={socket.factory} socketUrl="ws://test/ws" speakerFactory={audio.factory} />);
  act(() => {
    socket.open();
    socket.emit({ type: "conversation", conversation_id: 1, messages: [] });
    socket.emit({ type: "state", state: "idle" });
  });
  await screen.findByRole("button", { name: "Mute voice" });
  await act(async () => {}); // let the voice setting reach the conversation state
  return { socket, api, audio };
}

describe("Digital Me speaking (user's point of view)", () => {
  it("speaks a reply: audio is queued, the avatar speaks it, subtitles follow the voice", async () => {
    const { socket, audio } = await start();
    await userEvent.type(screen.getByRole("textbox", { name: "Message" }), "Hello{Enter}");
    expect(audio.speaker.unlock).toHaveBeenCalled(); // audio allowed by the user's keypress

    act(() => {
      socket.emit({ type: "state", state: "thinking" });
      socket.emit({ type: "user_message", message: dto({ role: "user", content: "Hello" }) });
      socket.emit({ type: "state", state: "speaking" });
      socket.emit({ type: "assistant_delta", text: "Hi there! How are you?" });
      socket.emit({ type: "sentence", index: 0, text: "Hi there!", emotion: "happy" });
    });
    // text is streaming but nothing is audible yet
    expect(screen.getByRole("status")).toHaveTextContent("Thinking");
    expect(document.querySelector(".caption__text")).toHaveTextContent("");

    act(() => socket.emit(audioEvent(0, "Hi there!", "happy")));
    expect(audio.clips.map((c) => c.text)).toEqual(["Hi there!"]);

    act(() => audio.start(audio.clips[0]));
    expect(screen.getByRole("status")).toHaveTextContent("Speaking");
    expect(document.querySelector(".caption__text")).toHaveTextContent("Hi there!");
    expect(screen.getByRole("img")).toHaveAttribute("data-emotion", "happy");

    act(() => {
      socket.emit({ type: "assistant_done", message: dto({ content: "Hi there! How are you?" }) });
      socket.emit({ type: "speech_end" });
      socket.emit({ type: "state", state: "idle" });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Speaking"); // still audible
    act(() => audio.idle());
    expect(screen.getByRole("status")).toHaveTextContent("Ready");
  });

  it("Stop silences speech immediately and tells the server", async () => {
    const { socket, audio } = await start();
    act(() => {
      socket.emit({ type: "state", state: "speaking" });
      socket.emit(audioEvent(0, "A long answer."));
      audio.start(audio.clips[0]);
    });
    await userEvent.click(screen.getByRole("button", { name: "Stop reply" }));
    expect(audio.speaker.stop).toHaveBeenCalled();
    expect(socket.sent).toContainEqual({ type: "interrupt" });
  });

  it("mute stops speaking, saves the preference and ignores further audio", async () => {
    const { socket, api, audio } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Mute voice" }));
    expect(api.updateVoice).toHaveBeenCalledWith({ enabled: false });
    expect(audio.speaker.stop).toHaveBeenCalled();
    expect(await screen.findByRole("button", { name: "Unmute voice" })).toBeInTheDocument();
    act(() => socket.emit(audioEvent(0, "Should not play.")));
    expect(audio.clips).toEqual([]);
  });

  it("changes voice and speed and previews it from the voice panel", async () => {
    const { api } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    const panel = screen.getByRole("complementary", { name: "Voice settings" });
    expect(within(panel).getByText("British English")).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole("radio", { name: /Emma/ }));
    expect(api.updateVoice).toHaveBeenCalledWith({ voice: "bf_emma" });
    expect(within(panel).getByRole("radio", { name: /Emma/ })).toBeChecked();

    const slider = within(panel).getByRole("slider", { name: "Speaking speed" });
    fireEvent.change(slider, { target: { value: "1.05" } });
    fireEvent.change(slider, { target: { value: "1.1" } }); // dragging: only the final value is saved
    expect(within(panel).getByText("1.10×")).toBeInTheDocument();
    await waitFor(() => expect(api.updateVoice).toHaveBeenCalledWith({ speed: 1.1 }));
    expect(api.updateVoice).not.toHaveBeenCalledWith({ speed: 1.05 });

    await userEvent.click(within(panel).getByRole("button", { name: "Preview voice" }));
    expect(api.previewVoice).toHaveBeenCalledWith("bf_emma", 1.1);
    expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
  });

  it("can switch speaking off from the panel", async () => {
    const { api } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    await userEvent.click(screen.getByRole("switch", { name: /Speak replies aloud/ }));
    expect(api.updateVoice).toHaveBeenCalledWith({ enabled: false });
  });

  it("hides voice controls when the server has no voice", async () => {
    const socket = controllableSocket();
    render(
      <App
        api={fakeApi({ voice: async () => Promise.reject(new Error("404")) })}
        socketFactory={socket.factory}
        socketUrl="ws://test/ws"
        speakerFactory={fakeSpeaker().factory}
      />,
    );
    await waitFor(() => expect(screen.queryByRole("button", { name: "Voice settings" })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /mute voice/i })).not.toBeInTheDocument();
  });
});
