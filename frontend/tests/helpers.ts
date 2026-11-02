import { vi } from "vitest";

import type { ClientMessage, ConversationDTO, MessageDTO, ServerEvent, StatusDTO } from "../src/api/protocol";
import type { Api } from "../src/api/rest";
import type { SocketOptions } from "../src/api/socket";
import type { SocketFactory } from "../src/hooks/useDigitalMe";

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

export function fakeApi(overrides: Partial<Api> = {}, conversations: ConversationDTO[] = []): Api {
  return {
    status: vi.fn(async () => STATUS_OK),
    conversations: vi.fn(async () => conversations),
    deleteConversation: vi.fn(async () => undefined),
    ...overrides,
  };
}
