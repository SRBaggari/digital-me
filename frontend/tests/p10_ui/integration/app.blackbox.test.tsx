import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "../../../src/App";
import { VOICE, controllableSocket, dto, fakeApi, fakeSpeaker } from "../../helpers";

const textOnlyApi = () => fakeApi({ voice: async () => ({ ...VOICE, settings: { ...VOICE.settings, enabled: false } }) });

function start(api = textOnlyApi()) {
  const socket = controllableSocket();
  const audio = fakeSpeaker();
  render(<App api={api} socketFactory={socket.factory} socketUrl="ws://test/ws" speakerFactory={audio.factory} />);
  act(() => {
    socket.open();
    socket.emit({ type: "conversation", conversation_id: 1, messages: [] });
    socket.emit({ type: "state", state: "idle" });
  });
  return { socket, api, audio };
}

describe("Digital Me app (user's point of view)", () => {
  it("shows the persona, the AI disclosure and that the model is local", async () => {
    start();
    expect(await screen.findByRole("heading", { name: "Sam Lee" })).toBeInTheDocument();
    expect(screen.getByText(/AI-generated digital human/)).toBeInTheDocument();
    expect(await screen.findByTestId("model-health")).toHaveTextContent("on this PC");
  });

  it("holds a full typed conversation", async () => {
    const { socket } = start();
    await userEvent.type(screen.getByRole("textbox", { name: "Message" }), "Hi there{Enter}");
    expect(socket.sent).toEqual([{ type: "user_message", text: "Hi there" }]);
    expect(screen.getByText("Hi there")).toBeInTheDocument();

    act(() => {
      socket.emit({ type: "state", state: "thinking" });
      socket.emit({ type: "user_message", message: dto({ role: "user", content: "Hi there" }) });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Thinking");
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", "Sam Lee is thinking");
    expect(screen.getByLabelText("Sam Lee is thinking", { selector: ".thinking" })).toBeInTheDocument();

    act(() => {
      socket.emit({ type: "emotion", emotion: "happy" });
      socket.emit({ type: "state", state: "speaking" });
      socket.emit({ type: "assistant_delta", text: "Hello! " });
      socket.emit({ type: "sentence", index: 0, text: "Hello!", emotion: "happy" });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Speaking");
    expect(screen.getByRole("img")).toHaveAttribute("data-emotion", "happy");
    expect(document.querySelector(".caption__text")).toHaveTextContent("Hello!");

    act(() => {
      socket.emit({ type: "assistant_delta", text: "Nice to meet you." });
      socket.emit({ type: "assistant_done", message: dto({ content: "Hello! Nice to meet you.", emotion: "happy" }) });
      socket.emit({ type: "state", state: "idle" });
    });
    const log = screen.getByRole("log");
    expect(within(log).getByText("Hello! Nice to meet you.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Ready");
  });

  it("stops a reply with the Stop button", async () => {
    const { socket } = start();
    act(() => {
      socket.emit({ type: "state", state: "speaking" });
      socket.emit({ type: "assistant_delta", text: "A long answer" });
    });
    await userEvent.click(screen.getByRole("button", { name: "Stop reply" }));
    expect(socket.sent).toContainEqual({ type: "interrupt" });
    act(() => {
      socket.emit({ type: "assistant_interrupted" });
      socket.emit({ type: "state", state: "idle" });
    });
    expect(screen.getByText("Stopped")).toBeInTheDocument();
  });

  it("starts a suggested conversation with one click", async () => {
    const { socket } = start();
    await userEvent.click(screen.getByRole("button", { name: "Tell me a little about yourself." }));
    expect(socket.sent).toEqual([{ type: "user_message", text: "Tell me a little about yourself." }]);
  });

  it("holds a conversation in Telugu", async () => {
    const { socket } = start();
    expect(screen.getByText(/English or Telugu/)).toBeInTheDocument(); // hint on an empty chat
    await userEvent.click(screen.getByRole("button", { name: "మీ గురించి కొంచెం చెప్పండి." }));
    expect(socket.sent).toEqual([{ type: "user_message", text: "మీ గురించి కొంచెం చెప్పండి." }]);
    act(() => {
      socket.emit({ type: "user_message", message: dto({ role: "user", content: "మీ గురించి కొంచెం చెప్పండి." }) });
      socket.emit({ type: "assistant_done", message: dto({ content: "నేను సాఫ్ట్‌వేర్ ఇంజనీర్‌ని." }) });
    });
    expect(within(screen.getByRole("log")).getByText("నేను సాఫ్ట్‌వేర్ ఇంజనీర్‌ని.")).toBeInTheDocument();
  });

  it("starts a new conversation", async () => {
    const { socket } = start();
    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(socket.sent).toEqual([{ type: "new_conversation" }]);
  });

  it("opens and deletes conversations from history", async () => {
    const api = fakeApi({}, [
      { id: 1, started_at: new Date().toISOString(), title: "Current chat", message_count: 2 },
      { id: 2, started_at: new Date().toISOString(), title: "Old chat", message_count: 4 },
      { id: 3, started_at: new Date().toISOString(), title: null, message_count: 0 },
    ]);
    const { socket } = start(api);
    await userEvent.click(screen.getByRole("button", { name: "Conversation history" }));
    const drawer = screen.getByRole("complementary", { name: "Conversation history" });
    expect(await within(drawer).findByText("Old chat")).toBeInTheDocument();
    expect(within(drawer).queryByText("New conversation")).not.toBeInTheDocument(); // empty ones hidden

    await userEvent.click(within(drawer).getByRole("button", { name: "Delete Old chat" }));
    await userEvent.click(within(drawer).getByRole("button", { name: "Delete" }));
    expect(api.deleteConversation).toHaveBeenCalledWith(2);
    await waitFor(() => expect(within(drawer).queryByText("Old chat")).not.toBeInTheDocument());

    await userEvent.click(within(drawer).getByText("Current chat"));
    expect(socket.sent).toContainEqual({ type: "open_conversation", conversation_id: 1 });
  });

  it("deleting the current conversation starts a fresh one", async () => {
    const api = fakeApi({}, [{ id: 1, started_at: new Date().toISOString(), title: "Current chat", message_count: 2 }]);
    const { socket } = start(api);
    await userEvent.click(screen.getByRole("button", { name: "Conversation history" }));
    await userEvent.click(await screen.findByRole("button", { name: "Delete Current chat" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(socket.sent).toContainEqual({ type: "new_conversation" }));
  });

  it("shows model errors from the server", async () => {
    const { socket } = start();
    act(() => socket.emit({ type: "error", code: "llm_error", detail: "Cannot reach Ollama." }));
    expect(screen.getByRole("alert")).toHaveTextContent("Cannot reach Ollama.");
  });

  it("warns when the connection drops and disables sending", async () => {
    const { socket } = start();
    act(() => socket.drop());
    expect(screen.getByRole("alert")).toHaveTextContent("Reconnecting");
    expect(screen.getByRole("textbox", { name: "Message" })).toHaveAttribute("placeholder", "Connecting…");
  });

  it("reports an offline server", async () => {
    start(fakeApi({ status: async () => Promise.reject(new Error("down")) }));
    await waitFor(() => expect(screen.getByTestId("model-health")).toHaveTextContent("Server offline"));
  });
});
