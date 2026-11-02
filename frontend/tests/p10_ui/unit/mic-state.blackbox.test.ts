import { describe, expect, it } from "vitest";

import type { ServerEvent } from "../../../src/api/protocol";
import { chatReducer, displayState, initialChatState, type ChatAction, type ChatState } from "../../../src/state/chat";

const run = (state: ChatState, ...actions: ChatAction[]) => actions.reduce(chatReducer, state);
const server = (event: ServerEvent): ChatAction => ({ type: "server", event });
const micOn = run(initialChatState, { type: "mic", status: "on" });

describe("avatar state while talking by voice", () => {
  it("with the microphone open and nothing happening, the avatar is listening", () => {
    expect(displayState(micOn)).toBe("listening");
    expect(displayState(initialChatState)).toBe("idle");
  });

  it("when the user speaks, the avatar listens, even over its own voice", () => {
    const s = run(micOn, { type: "clip_start", text: "x", emotion: "neutral" }, server({ type: "user_speaking", speaking: true }));
    expect(displayState(s)).toBe("listening");
  });

  it("while transcribing, the avatar is thinking", () => {
    const s = run(micOn, server({ type: "transcribing" }));
    expect(s.transcribing).toBe(true);
    expect(displayState(s)).toBe("thinking");
    expect(run(s, server({ type: "transcript", text: "hi" })).transcribing).toBe(false);
  });

  it("barge-in stops playback", () => {
    const s = run(micOn, { type: "clip_start", text: "x", emotion: "neutral" }, server({ type: "barge_in" }));
    expect(s.playing).toBe(false);
  });

  it("a microphone failure is shown and the microphone is off", () => {
    const s = run(initialChatState, { type: "mic", status: "starting" }, { type: "mic_error", detail: "blocked" });
    expect(s.mic).toBe("off");
    expect(s.error).toEqual({ code: "mic_error", detail: "blocked" });
  });

  it("switching the mic off, losing the connection or a new conversation clears speaking indicators", () => {
    const speaking = run(micOn, server({ type: "user_speaking", speaking: true }), server({ type: "transcribing" }));
    for (const action of [
      { type: "mic", status: "off" } as ChatAction,
      { type: "connection", status: "closed" } as ChatAction,
      server({ type: "conversation", conversation_id: 2, messages: [] }),
    ]) {
      const s = run(speaking, action);
      expect([s.userSpeaking, s.transcribing]).toEqual([false, false]);
    }
  });
});
