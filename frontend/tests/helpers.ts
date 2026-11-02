import { vi } from "vitest";

import type {
  AudioEvent,
  ClientMessage,
  ConversationDTO,
  MessageDTO,
  ServerEvent,
  StatusDTO,
  VoiceDTO,
  VoiceSettingsDTO,
} from "../src/api/protocol";
import type { Api } from "../src/api/rest";
import type { SocketOptions } from "../src/api/socket";
import type { SpeechClip, SpeechQueueEvents } from "../src/audio/speechQueue";
import type { SocketFactory, SpeakerFactory } from "../src/hooks/useDigitalMe";

/** Minimal stand-in for the browser WebSocket, driven manually by tests. */
export class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readyState = FakeWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  static latest(): FakeWebSocket {
    return FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  }

  static reset(): void {
    FakeWebSocket.instances = [];
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    if (this.readyState === FakeWebSocket.CLOSED) return;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }

  serverOpen(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }

  serverSend(event: ServerEvent | string): void {
    this.onmessage?.({ data: typeof event === "string" ? event : JSON.stringify(event) });
  }

  serverClose(): void {
    this.close();
  }
}

export const AsWebSocket = FakeWebSocket as unknown as typeof WebSocket;

/** A socket factory whose sockets are fully controlled by the test. */
export function controllableSocket() {
  let options: SocketOptions | null = null;
  const sent: ClientMessage[] = [];
  let open = false;
  const factory: SocketFactory = (opts) => {
    options = opts;
    return {
      connect: () => opts.onStatus("connecting"),
      send: (message) => {
        if (!open) return false;
        sent.push(message);
        return true;
      },
      close: () => {
        open = false;
      },
    };
  };
  return {
    factory,
    sent,
    open() {
      open = true;
      options!.onStatus("open");
    },
    drop() {
      open = false;
      options!.onStatus("closed");
    },
    emit(event: ServerEvent) {
      options!.onEvent(event);
    },
  };
}

let nextId = 1;

export function dto(partial: Partial<MessageDTO> = {}): MessageDTO {
  return {
    id: nextId++,
    conversation_id: 1,
    role: "assistant",
    content: "hello",
    emotion: "neutral",
    interrupted: false,
    created_at: "2026-11-02T10:00:00+00:00",
    ...partial,
  };
}

export const STATUS_OK: StatusDTO = {
  instance: "test",
  persona_name: "Sam Lee",
  model: "llama3.2:3b",
  llm: { reachable: true, model_available: true, detail: "" },
  disclosure: "AI-generated digital human. Not a real person communicating live.",
};

export const VOICE: VoiceDTO = {
  settings: { enabled: true, voice: "af_heart", speed: 1 },
  voices: [
    { id: "af_heart", name: "Heart", accent: "American", gender: "female" },
    { id: "am_michael", name: "Michael", accent: "American", gender: "male" },
    { id: "bf_emma", name: "Emma", accent: "British", gender: "female" },
  ],
  engine: "kokoro",
  status: "ready",
};

export function fakeApi(overrides: Partial<Api> = {}, conversations: ConversationDTO[] = []): Api {
  let voice = structuredClone(VOICE);
  return {
    status: vi.fn(async () => STATUS_OK),
    conversations: vi.fn(async () => conversations),
    deleteConversation: vi.fn(async () => undefined),
    voice: vi.fn(async () => voice),
    updateVoice: vi.fn(async (change: Partial<VoiceSettingsDTO>) => {
      voice = { ...voice, settings: { ...voice.settings, ...change } };
      return voice;
    }),
    previewVoice: vi.fn(async () => new Blob(["RIFF"], { type: "audio/wav" })),
    ...overrides,
  };
}

/** Speaker that records clips and lets tests drive playback start/end. */
export function fakeSpeaker() {
  const clips: SpeechClip[] = [];
  let events: SpeechQueueEvents = {};
  const speaker = {
    enqueue: vi.fn((clip: SpeechClip) => clips.push(clip)),
    stop: vi.fn(),
    unlock: vi.fn(),
    level: vi.fn(() => 0.5),
  };
  const factory: SpeakerFactory = (e) => {
    events = e;
    return speaker;
  };
  return {
    factory,
    speaker,
    clips,
    start(clip: SpeechClip) {
      events.onClipStart?.(clip);
    },
    idle() {
      events.onIdle?.();
    },
  };
}

export function audioEvent(index: number, text: string, emotion: AudioEvent["emotion"] = "neutral"): AudioEvent {
  return {
    type: "audio",
    index,
    text,
    emotion,
    sample_rate: 24000,
    duration: 1,
    format: "wav",
    data: btoa("RIFF"),
    words: [],
  };
}
