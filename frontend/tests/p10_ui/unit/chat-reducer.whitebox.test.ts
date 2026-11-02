import { describe, expect, it } from "vitest";

import { chatReducer, fromDTO, initialChatState, isResponding, type ChatState } from "../../../src/state/chat";
import { dto } from "../../helpers";

const send = (state: ChatState, text: string) => chatReducer(state, { type: "send", text, now: "t" });
const server = (state: ChatState, event: Parameters<typeof chatReducer>[1] & { type: "server" }) =>
  chatReducer(state, event);

describe("chatReducer internals", () => {
  it("gives optimistic messages unique local keys from a counter", () => {
    const s = send(send(initialChatState, "a"), "b");
    expect(s.messages.map((m) => m.key)).toEqual(["local1", "local2"]);
    expect(s.localCounter).toBe(2);
    expect(s.messages.every((m) => m.pending)).toBe(true);
  });

  it("replaces only the first pending user message on confirmation", () => {
    let s = send(send(initialChatState, "a"), "b");
    s = server(s, { type: "server", event: { type: "user_message", message: dto({ role: "user", content: "a", id: 7 }) } });
    expect(s.messages.map((m) => [m.key, m.pending])).toEqual([
      ["m7", false],
      ["local2", true],
    ]);
  });

  it("appends a confirmed user message when nothing is pending", () => {
    const s = server(initialChatState, { type: "server", event: { type: "user_message", message: dto({ role: "user" }) } });
    expect(s.messages).toHaveLength(1);
  });

  it("moves a streaming draft into the transcript when the user sends again", () => {
    let s = server(initialChatState, { type: "server", event: { type: "assistant_delta", text: "partial " } });
    s = send(s, "new question");
    expect(s.draft).toBeNull();
    expect(s.messages[0]).toMatchObject({ role: "assistant", content: "partial", interrupted: true });
    expect(s.messages[1]).toMatchObject({ role: "user", pending: true });
  });

  it("keeps draft emotion in sync with emotion events", () => {
    let s = server(initialChatState, { type: "server", event: { type: "assistant_delta", text: "x" } });
    s = server(s, { type: "server", event: { type: "emotion", emotion: "sad" } });
    expect(s.draft?.emotion).toBe("sad");
  });

  it("starts a draft with the current emotion", () => {
    let s = server(initialChatState, { type: "server", event: { type: "emotion", emotion: "happy" } });
    s = server(s, { type: "server", event: { type: "assistant_delta", text: "x" } });
    expect(s.draft).toEqual({ text: "x", emotion: "happy" });
  });

  it("drops an empty draft on interruption without adding a message", () => {
    let s = server(initialChatState, { type: "server", event: { type: "assistant_delta", text: "   " } });
    s = server(s, { type: "server", event: { type: "assistant_interrupted" } });
    expect(s.messages).toEqual([]);
    expect(s.draft).toBeNull();
  });

  it("removes pending messages only for errors where the server stored nothing", () => {
    const pending = send(initialChatState, "x");
    expect(server(pending, { type: "server", event: { type: "error", code: "invalid_input", detail: "" } }).messages).toEqual([]);
    expect(server(pending, { type: "server", event: { type: "error", code: "llm_error", detail: "" } }).messages).toHaveLength(1);
  });

  it("clears draft and avatar state when the connection closes", () => {
    let s = server(initialChatState, { type: "server", event: { type: "state", state: "speaking" } });
    s = server(s, { type: "server", event: { type: "assistant_delta", text: "x" } });
    s = chatReducer(s, { type: "connection", status: "closed" });
    expect(s.draft).toBeNull();
    expect(s.avatarState).toBe("idle");
  });

  it("keeps state on reconnecting status", () => {
    const s = server(initialChatState, { type: "server", event: { type: "assistant_delta", text: "x" } });
    expect(chatReducer(s, { type: "connection", status: "connecting" }).draft).not.toBeNull();
  });

  it("maps unknown stored emotions to neutral and user emotions to null", () => {
    expect(fromDTO(dto({ emotion: "furious" })).emotion).toBe("neutral");
    expect(fromDTO(dto({ role: "user", emotion: "happy" })).emotion).toBeNull();
  });

  it("isResponding covers thinking, speaking and an open draft", () => {
    expect(isResponding(initialChatState)).toBe(false);
    expect(isResponding({ ...initialChatState, avatarState: "thinking" })).toBe(true);
    expect(isResponding({ ...initialChatState, avatarState: "speaking" })).toBe(true);
    expect(isResponding({ ...initialChatState, draft: { text: "", emotion: "neutral" } })).toBe(true);
  });
});
