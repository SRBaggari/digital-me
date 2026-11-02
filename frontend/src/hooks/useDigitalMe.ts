import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";

import { MAX_INPUT_CHARS, type ClientMessage } from "../api/protocol";
import { DigitalMeSocket, defaultSocketUrl, type SocketOptions } from "../api/socket";
import { BrowserMicrophone, explainMicError, type Mic } from "../audio/microphone";
import { SpeechQueue, type SpeechQueueEvents } from "../audio/speechQueue";
import { WebAudioBackend } from "../audio/webAudioBackend";
import { chatReducer, displayState, initialChatState, isResponding } from "../state/chat";

export type SocketFactory = (
  options: SocketOptions,
) => Pick<DigitalMeSocket, "connect" | "send" | "sendBinary" | "close">;
export type Speaker = Pick<SpeechQueue, "enqueue" | "stop" | "unlock" | "level">;
export type SpeakerFactory = (events: SpeechQueueEvents) => Speaker;
export type MicFactory = () => Mic;

const defaultSocketFactory: SocketFactory = (options) => new DigitalMeSocket(options);
const defaultSpeakerFactory: SpeakerFactory = (events) => new SpeechQueue(new WebAudioBackend(), events);
const defaultMicFactory: MicFactory = () => new BrowserMicrophone();

/** Connects to the backend and exposes the conversation state plus the actions the UI needs. */
export function useDigitalMe(
  createSocket: SocketFactory = defaultSocketFactory,
  url?: string,
  createSpeaker: SpeakerFactory = defaultSpeakerFactory,
  createMic: MicFactory = defaultMicFactory,
) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const socketRef = useRef<ReturnType<SocketFactory> | null>(null);
  const voiceEnabledRef = useRef(state.voiceEnabled);
  voiceEnabledRef.current = state.voiceEnabled;
  const playingRef = useRef(state.playing);
  playingRef.current = state.playing;
  const micStatusRef = useRef(state.mic);
  micStatusRef.current = state.mic;

  const speaker = useMemo(
    () =>
      createSpeaker({
        onClipStart: (clip) => dispatch({ type: "clip_start", text: clip.text, emotion: clip.emotion }),
        onIdle: () => dispatch({ type: "playback_idle" }),
      }),
    [createSpeaker],
  );
  const mic = useMemo(() => createMic(), [createMic]);

  useEffect(
    () => () => {
      speaker.stop();
      mic.stop();
    },
    [speaker, mic],
  );

  useEffect(() => {
    const socket = createSocket({
      url: url ?? defaultSocketUrl(),
      onEvent: (event) => {
        if (event.type === "audio") {
          if (voiceEnabledRef.current) speaker.enqueue(event);
          return;
        }
        if (event.type === "conversation" || event.type === "barge_in") speaker.stop();
        if (event.type === "error" && event.code === "not_available" && micStatusRef.current !== "off") {
          mic.stop(); // the server cannot listen: don't keep the microphone open for nothing
          dispatch({ type: "mic", status: "off" });
        }
        dispatch({ type: "server", event });
      },
      onStatus: (status) => {
        dispatch({ type: "connection", status });
        // After a reconnect the server has forgotten the open microphone: tell it again.
        if (status === "open" && micStatusRef.current === "on") socket.send({ type: "mic_start" });
      },
    });
    socketRef.current = socket;
    socket.connect();
    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [createSocket, url, speaker, mic]);

  const send = useCallback((message: ClientMessage) => socketRef.current?.send(message) ?? false, []);

  // Let the server know when Digital Me is audible, so its own voice isn't taken for the user.
  useEffect(() => {
    send({ type: "playback", playing: state.playing });
  }, [state.playing, send]);

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

  // The ref is updated immediately (not on the next render) so that a quick double-click
  // cannot open the microphone twice.
  const stopMic = useCallback(() => {
    micStatusRef.current = "off";
    mic.stop();
    send({ type: "mic_stop" });
    dispatch({ type: "mic", status: "off" });
  }, [mic, send]);

  const startMic = useCallback(async () => {
    if (micStatusRef.current !== "off") return;
    micStatusRef.current = "starting";
    speaker.unlock(); // the click that opens the mic also allows audio playback
    dispatch({ type: "mic", status: "starting" });
    try {
      await mic.start({ onFrame: (pcm) => socketRef.current?.sendBinary(pcm) });
    } catch (error) {
      micStatusRef.current = "off";
      dispatch({ type: "mic_error", detail: explainMicError(error).message });
      return;
    }
    if (micStatusRef.current !== "starting") {
      mic.stop(); // switched off while the browser was still asking for permission
      return;
    }
    micStatusRef.current = "on";
    send({ type: "mic_start" });
    dispatch({ type: "mic", status: "on" });
  }, [mic, send, speaker]);

  const toggleMic = useCallback(() => {
    if (micStatusRef.current === "off") void startMic();
    else stopMic();
  }, [startMic, stopMic]);

  const setVoiceEnabled = useCallback(
    (enabled: boolean) => {
      if (!enabled) speaker.stop();
      else speaker.unlock();
      dispatch({ type: "voice_enabled", enabled });
    },
    [speaker],
  );

  // The presence follows whoever is talking: Digital Me's voice, or the user's microphone.
  const level = useCallback(
    () => (playingRef.current ? speaker.level() : micStatusRef.current === "on" ? mic.level() : 0),
    [speaker, mic],
  );

  return {
    state,
    avatarState: displayState(state),
    responding: isResponding(state),
    level,
    sendText,
    interrupt,
    toggleMic,
    stopMic,
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
