// Mirrors backend/digital_me/server/protocol.py.

export const EMOTIONS = ["neutral", "happy", "serious", "surprised", "sad", "empathetic"] as const;
export type Emotion = (typeof EMOTIONS)[number];

export const AVATAR_STATES = ["idle", "listening", "thinking", "speaking"] as const;
export type AvatarState = (typeof AVATAR_STATES)[number];

export interface MessageDTO {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  emotion: string | null;
  interrupted: boolean;
  created_at: string;
}

export interface ConversationDTO {
  id: number;
  started_at: string;
  title: string | null;
  message_count: number;
}

export interface StatusDTO {
  instance: string;
  persona_name: string;
  model: string;
  llm: { reachable: boolean; model_available: boolean; detail: string };
  disclosure: string;
  /** off | loading | ready | error: ... */
  speech?: string;
}

export interface WordTimingDTO {
  text: string;
  start: number;
  end: number;
  phonemes: string;
}

export interface AudioEvent {
  type: "audio";
  index: number;
  text: string;
  emotion: Emotion;
  sample_rate: number;
  duration: number;
  format: "wav";
  /** base64-encoded WAV */
  data: string;
  words: WordTimingDTO[];
}

export interface VoiceOption {
  id: string;
  name: string;
  accent: string;
  gender: string;
}

export interface VoiceSettingsDTO {
  enabled: boolean;
  voice: string;
  speed: number;
}

export interface VoiceDTO {
  settings: VoiceSettingsDTO;
  voices: VoiceOption[];
  engine: string;
  status: string;
}

export type ServerEvent =
  | { type: "conversation"; conversation_id: number; messages: MessageDTO[] }
  | { type: "state"; state: AvatarState }
  | { type: "user_message"; message: MessageDTO }
  | { type: "emotion"; emotion: Emotion }
  | { type: "assistant_delta"; text: string }
  | { type: "sentence"; index: number; text: string; emotion: Emotion }
  | { type: "assistant_done"; message: MessageDTO }
  | { type: "assistant_interrupted" }
  | AudioEvent
  | { type: "speech_end" }
  | { type: "error"; code: string; detail: string };

export type ClientMessage =
  | { type: "user_message"; text: string }
  | { type: "interrupt" }
  | { type: "new_conversation" }
  | { type: "open_conversation"; conversation_id: number };

export const MAX_INPUT_CHARS = 4000;

export function toEmotion(value: unknown): Emotion {
  return (EMOTIONS as readonly unknown[]).includes(value) ? (value as Emotion) : "neutral";
}

const SERVER_EVENT_TYPES = new Set([
  "conversation",
  "state",
  "user_message",
  "emotion",
  "assistant_delta",
  "sentence",
  "assistant_done",
  "assistant_interrupted",
  "audio",
  "speech_end",
  "error",
]);

/** Parse a raw WebSocket frame; returns null for anything that is not a known event. */
export function parseServerEvent(raw: string): ServerEvent | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const type = (data as { type?: unknown }).type;
  return typeof type === "string" && SERVER_EVENT_TYPES.has(type) ? (data as ServerEvent) : null;
}
