import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "../../../src/App";
import { MicrophoneError } from "../../../src/audio/microphone";
import { LISTENING, controllableSocket, dto, fakeApi, fakeMic, fakeSpeaker } from "../../helpers";

async function start({ api = fakeApi(), micError }: { api?: ReturnType<typeof fakeApi>; micError?: unknown } = {}) {
  const socket = controllableSocket();
  const audio = fakeSpeaker();
  const microphone = fakeMic(micError);
  render(
    <App
      api={api}
      socketFactory={socket.factory}
      socketUrl="ws://test/ws"
      speakerFactory={audio.factory}
      micFactory={microphone.factory}
    />,
  );
  act(() => {
    socket.open();
    socket.emit({ type: "conversation", conversation_id: 1, messages: [] });
    socket.emit({ type: "state", state: "idle" });
  });
  await screen.findByRole("button", { name: /turn microphone on/ });
  await act(async () => {});
  return { socket, audio, microphone, api };
}

const micButton = (state: "on" | "off") =>
  screen.getByRole("button", { name: state === "off" ? /turn microphone on/ : /turn microphone off/ });

describe("talking to Digital Me with your voice", () => {
  it("a full spoken turn: mic on, speak, see what was heard, get a reply", async () => {
    const { socket, microphone } = await start();
    await userEvent.click(micButton("off"));
    expect(microphone.mic.start).toHaveBeenCalled();
    expect(socket.sent).toContainEqual({ type: "mic_start" });
    expect(micButton("on")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("status", { name: "" })).toBeTruthy;
    expect(screen.getByText(/Listening: just talk/)).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("data-state", "listening");

    act(() => microphone.frame(1024));
    expect(socket.binary).toHaveLength(1); // audio goes to the server as binary frames

    act(() => socket.emit({ type: "user_speaking", speaking: true }));
    expect(screen.getByLabelText("Listening to you")).toHaveTextContent("Listening…");

    act(() => {
      socket.emit({ type: "user_speaking", speaking: false });
      socket.emit({ type: "transcribing" });
    });
    expect(screen.getByLabelText("Transcribing")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("data-state", "thinking");

    act(() => {
      socket.emit({ type: "transcript", text: "Do you like jazz?" });
      socket.emit({ type: "state", state: "thinking" });
      socket.emit({ type: "user_message", message: dto({ role: "user", content: "Do you like jazz?" }) });
      socket.emit({ type: "assistant_delta", text: "I love it." });
      socket.emit({ type: "assistant_done", message: dto({ content: "I love it." }) });
      socket.emit({ type: "state", state: "idle" });
    });
    const log = screen.getByRole("log");
    expect(within(log).getByText("Do you like jazz?")).toBeInTheDocument();
    expect(within(log).getByText("I love it.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Transcribing")).not.toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("data-state", "listening"); // ready for more
  });

  it("clicking the mic again stops listening", async () => {
    const { socket, microphone } = await start();
    await userEvent.click(micButton("off"));
    await userEvent.click(micButton("on"));
    expect(microphone.mic.stop).toHaveBeenCalled();
    expect(socket.sent).toContainEqual({ type: "mic_stop" });
    expect(micButton("off")).toHaveAttribute("aria-pressed", "false");
  });

  it("explains a blocked microphone", async () => {
    await start({ micError: new MicrophoneError("denied", "Microphone access was blocked. Allow it in the browser's address bar.") });
    await userEvent.click(micButton("off"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Microphone access was blocked");
    expect(micButton("off")).toBeEnabled();
  });

  it("talking over a reply silences it (barge-in)", async () => {
    const { socket, audio } = await start();
    await userEvent.click(micButton("off"));
    act(() => socket.emit({ type: "barge_in" }));
    expect(audio.speaker.stop).toHaveBeenCalled();
  });

  it("no microphone button when voice input is switched off", async () => {
    const api = fakeApi({ listening: vi.fn(async () => ({ ...LISTENING, settings: { enabled: false, barge_in: true } })) });
    render(
      <App api={api} socketFactory={controllableSocket().factory} speakerFactory={fakeSpeaker().factory} micFactory={fakeMic().factory} />,
    );
    await waitFor(() => expect(api.listening).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.queryByRole("button", { name: /microphone/ })).not.toBeInTheDocument();
  });

  it("more accurate Telugu recognition can be switched on and off", async () => {
    const { api } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    const toggle = screen.getByRole("switch", { name: /More accurate Telugu recognition/ });
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    expect(api.updateListening).toHaveBeenCalledWith({ telugu_model: "small" });
    await waitFor(() => expect(toggle).toBeChecked());
    await userEvent.click(toggle);
    expect(api.updateListening).toHaveBeenCalledWith({ telugu_model: "base" });
  });

  it("no Telugu accuracy option for an English-only instance", async () => {
    await start({ api: fakeApi({ listening: vi.fn(async () => ({ ...LISTENING, languages: ["en"] })) }) });
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    expect(screen.queryByRole("switch", { name: /Telugu recognition/ })).not.toBeInTheDocument();
  });

  it("the instant acknowledgement can be switched off", async () => {
    const { api } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    const toggle = screen.getByRole("switch", { name: /Instant acknowledgement/ });
    expect(toggle).toBeChecked();
    await userEvent.click(toggle);
    expect(api.updateVoice).toHaveBeenCalledWith({ acknowledge: false });
  });

  it("voice-input options in the settings panel", async () => {
    const { api } = await start();
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    const panel = screen.getByRole("complementary", { name: "Voice settings" });
    expect(within(panel).getByText(/Speech recognition ready \(base.en\)/)).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("switch", { name: /Interrupt by talking/ }));
    expect(api.updateListening).toHaveBeenCalledWith({ barge_in: false });
    await userEvent.click(within(panel).getByRole("switch", { name: /Voice input/ }));
    expect(api.updateListening).toHaveBeenCalledWith({ enabled: false });
    await waitFor(() => expect(screen.queryByRole("button", { name: /microphone/ })).not.toBeInTheDocument());
  });

  it("switching voice input off while listening closes the microphone", async () => {
    const { microphone, socket } = await start();
    await userEvent.click(micButton("off"));
    await userEvent.click(screen.getByRole("button", { name: "Voice settings" }));
    await userEvent.click(screen.getByRole("switch", { name: /Voice input/ }));
    await waitFor(() => expect(microphone.mic.stop).toHaveBeenCalled());
    expect(socket.sent).toContainEqual({ type: "mic_stop" });
  });
});
