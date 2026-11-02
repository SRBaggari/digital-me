import { describe, expect, it } from "vitest";

import type { ServerEvent } from "../../../src/api/protocol";
import { chatReducer, initialChatState, type ChatState } from "../../../src/state/chat";
import { dto } from "../../helpers";

function play(events: ServerEvent[], start: ChatState = initialChatState): ChatState {
  return events.reduce((state, event) => chatReducer(state, { type: "server", event }), start);
}

describe("chat state from a stream of server events", () => {
  it("loads a conversation", () => {
    const s = play([
      { type: "conversation", conversation_id: 4, messages: [dto({ role: "user", content: "hi" }), dto({ content: "hey" })] },
    ]);
    expect(s.conversationId).toBe(4);
    expect(s.messages.map((m) => m.content)).toEqual(["hi", "hey"]);
  });

  it("produces a complete turn", () => {
    const s = play([
      { type: "state", state: "thinking" },
      { type: "user_message", message: dto({ role: "user", content: "hi" }) },
      { type: "emotion", emotion: "happy" },
      { type: "state", state: "speaking" },
      { type: "assistant_delta", text: "Hello " },
      { type: "assistant_delta", text: "there." },
      { type: "sentence", index: 0, text: "Hello there.", emotion: "happy" },
      { type: "assistant_done", message: dto({ content: "Hello there.", emotion: "happy" }) },
      { type: "state", state: "idle" },
    ]);
    expect(s.messages.map((m) => [m.role, m.content])).toEqual([
      ["user", "hi"],
      ["assistant", "Hello there."],
    ]);
    expect(s.draft).toBeNull();
    expect(s.caption).toBe("Hello there.");
    expect(s.emotion).toBe("happy");
    expect(s.avatarState).toBe("idle");
  });

  it("shows streamed text before the reply is done", () => {
    const s = play([
      { type: "assistant_delta", text: "Hel" },
      { type: "assistant_delta", text: "lo" },
    ]);
    expect(s.draft?.text).toBe("Hello");
  });

  it("keeps an interrupted reply marked as stopped", () => {
    const s = play([{ type: "assistant_delta", text: "Half a thou" }, { type: "assistant_interrupted" }]);
    expect(s.messages).toHaveLength(1);
    expect(s.messages[0]).toMatchObject({ content: "Half a thou", interrupted: true });
  });

  it("records errors and lets them be dismissed", () => {
    const s = play([{ type: "error", code: "llm_error", detail: "Ollama offline" }]);
    expect(s.error).toEqual({ code: "llm_error", detail: "Ollama offline" });
    expect(chatReducer(s, { type: "dismiss_error" }).error).toBeNull();
  });

  it("a new conversation resets transcript, caption and emotion", () => {
    const s = play([
      { type: "emotion", emotion: "sad" },
      { type: "sentence", index: 0, text: "x", emotion: "sad" },
      { type: "conversation", conversation_id: 9, messages: [] },
    ]);
    expect(s).toMatchObject({ conversationId: 9, messages: [], caption: "", emotion: "neutral" });
  });

  it("ignores unknown emotions", () => {
    expect(play([{ type: "emotion", emotion: "rage" as never }]).emotion).toBe("neutral");
  });

  it("sending clears a previous error", () => {
    const errored = play([{ type: "error", code: "llm_error", detail: "x" }]);
    expect(chatReducer(errored, { type: "send", text: "retry", now: "t" }).error).toBeNull();
  });
});
