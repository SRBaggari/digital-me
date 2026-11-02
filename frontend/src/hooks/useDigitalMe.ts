import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";

import { MAX_INPUT_CHARS, type ClientMessage } from "../api/protocol";
import { DigitalMeSocket, defaultSocketUrl, type SocketOptions } from "../api/socket";
import { SpeechQueue, type SpeechQueueEvents } from "../audio/speechQueue";
import { WebAudioBackend } from "../audio/webAudioBackend";
import { chatReducer, displayState, initialChatState, isResponding } from "../state/chat";

export type SocketFactory = (options: SocketOptions) => Pick<DigitalMeSocket, "connect" | "send" | "close">;
export type Speaker = Pick<SpeechQueue, "enqueue" | "stop" | "unlock" | "level">;
export type SpeakerFactory = (events: SpeechQueueEvents) => Speaker;

const defaultSocketFactory: SocketFactory = (options) => new DigitalMeSocket(options);
const defaultSpeakerFactory: SpeakerFactory = (events) => new SpeechQueue(new WebAudioBackend(), events);

/** Connects to the backend and exposes the conversation state plus the actions the UI needs. */
export function useDigitalMe(
  createSocket: SocketFactory = defaultSocketFactory,
  url?: string,
  createSpeaker: SpeakerFactory = defaultSpeakerFactory,
) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const socketRef = useRef<ReturnType<SocketFactory> | null>(null);
  const voiceEnabledRef = useRef(state.voiceEnabled);
  voiceEnabledRef.current = state.voiceEnabled;

  const speaker = useMemo(
    () =>
      createSpeaker({
        onClipStart: (clip) => dispatch({ type: "clip_start", text: clip.text, emotion: clip.emotion }),
        onIdle: () => dispatch({ type: "playback_idle" }),
      }),
    [createSpeaker],
  );

  useEffect(() => () => speaker.stop(), [speaker]);

  useEffect(() => {
    const socket = createSocket({
      url: url ?? defaultSocketUrl(),
      onEvent: (event) => {
        if (event.type === "audio") {
          if (voiceEnabledRef.current) speaker.enqueue(event);
          return;
        }
        if (event.type === "conversation") speaker.stop();
        dispatch({ type: "server", event });
      },
      onStatus: (status) => dispatch({ type: "connection", status }),
    });
    socketRef.current = socket;
    socket.connect();
    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [createSocket, url, speaker]);

  const send = useCallback((message: ClientMessage) => socketRef.current?.send(message) ?? false, []);

  const sendText = useCallback(
    (raw: string): boolean => {
      const text = raw.trim();
      if (!text || text.length > MAX_INPUT_CHARS) return false;
      speaker.unlock(); // we are inside a user gesture: allowed to start audio
      if (!send({ type: "user_message", text })) return false;
      speaker.stop();
      dispatch({ type: "send", text, now: new Date().toISOString() });
      return true;
    },
    [send, speaker],
  );

  const interrupt = useCallback(() => {
    speaker.stop();
    return send({ type: "interrupt" });
  }, [send, speaker]);

  const setVoiceEnabled = useCallback(
    (enabled: boolean) => {
      if (!enabled) speaker.stop();
      else speaker.unlock();
      dispatch({ type: "voice_enabled", enabled });
    },
    [speaker],
  );

  return {
    state,
    avatarState: displayState(state),
    responding: isResponding(state),
    level: useCallback(() => speaker.level(), [speaker]),
    sendText,
    interrupt,
    setVoiceEnabled,
    newConversation: useCallback(() => send({ type: "new_conversation" }), [send]),
    openConversation: useCallback(
      (id: number) => send({ type: "open_conversation", conversation_id: id }),
      [send],
    ),
    dismissError: useCallback(() => dispatch({ type: "dismiss_error" }), []),
  };
}

export type DigitalMe = ReturnType<typeof useDigitalMe>;
