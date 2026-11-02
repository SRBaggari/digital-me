import { describe, expect, it } from "vitest";

import type { ServerEvent } from "../../../src/api/protocol";
import { chatReducer, displayState, initialChatState, isResponding, type ChatAction, type ChatState } from "../../../src/state/chat";
import { audioEvent } from "../../helpers";

const voiceOn = chatReducer(initialChatState, { type: "voice_enabled", enabled: true });
const run = (state: ChatState, ...actions: ChatAction[]) => actions.reduce(chatReducer, state);
const server = (event: ServerEvent): ChatAction => ({ type: "server", event });

describe("avatar state and subtitles with voice", () => {
  it("shows Thinking while the reply is generating but not yet audible", () => {
    const s = run(voiceOn, server({ type: "state", state: "speaking" }), server({ type: "assistant_delta", text: "Hi" }));
    expect(displayState(s)).toBe("thinking");
  });

  it("shows Speaking while audio plays, even after the server is idle", () => {
    const s = run(
      voiceOn,
      { type: "clip_start", text: "Hi!", emotion: "happy" },
      server({ type: "state", state: "idle" }),
    );
    expect(displayState(s)).toBe("speaking");
    expect(isResponding(s)).toBe(true);
    expect(displayState(run(s, { type: "playback_idle" }))).toBe("idle");
  });

  it("subtitles and expression follow what is being heard", () => {
    let s = run(
      voiceOn,
      server({ type: "emotion", emotion: "sad" }),
      server({ type: "sentence", index: 0, text: "Generated ahead.", emotion: "sad" }),
    );
    expect(s.caption).toBe("");
    expect(s.emotion).toBe("neutral");
    s = run(s, { type: "clip_start", text: "Heard now.", emotion: "sad" });
    expect(s.caption).toBe("Heard now.");
    expect(s.emotion).toBe("sad");
  });

  it("without voice, subtitles and expression follow the text immediately", () => {
    const s = run(
      initialChatState,
      server({ type: "emotion", emotion: "happy" }),
      server({ type: "sentence", index: 0, text: "Typed reply.", emotion: "happy" }),
    );
    expect(s.caption).toBe("Typed reply.");
    expect(s.emotion).toBe("happy");
    expect(displayState(run(s, server({ type: "state", state: "speaking" })))).toBe("speaking");
  });

  it("audio events do not change the transcript", () => {
    expect(run(voiceOn, server(audioEvent(0, "x")), server({ type: "speech_end" }))).toEqual(voiceOn);
  });

  it("sending a message, switching voice off or opening a conversation silences playback", () => {
    const playing = run(voiceOn, { type: "clip_start", text: "x", emotion: "neutral" });
    expect(run(playing, { type: "send", text: "new", now: "t" }).playing).toBe(false);
    expect(run(playing, { type: "voice_enabled", enabled: false }).playing).toBe(false);
    expect(run(playing, server({ type: "conversation", conversation_id: 2, messages: [] })).playing).toBe(false);
  });
});
