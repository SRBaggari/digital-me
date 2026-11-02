import { parseServerEvent, type ClientMessage, type ServerEvent } from "./protocol";

export type ConnectionStatus = "connecting" | "open" | "closed";

export interface SocketOptions {
  url: string;
  onEvent: (event: ServerEvent) => void;
  onStatus: (status: ConnectionStatus) => void;
  /** Injected in tests. */
  WebSocketImpl?: typeof WebSocket;
  minDelayMs?: number;
  maxDelayMs?: number;
}

export function defaultSocketUrl(loc: Pick<Location, "protocol" | "host"> = window.location): string {
  return `${loc.protocol === "https:" ? "wss" : "ws"}://${loc.host}/ws`;
}

/** WebSocket with automatic reconnection (exponential backoff, capped). */
export class DigitalMeSocket {
  private ws: WebSocket | null = null;
  private attempts = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private readonly WS: typeof WebSocket;
  private readonly minDelay: number;
  private readonly maxDelay: number;

  constructor(private readonly options: SocketOptions) {
    this.WS = options.WebSocketImpl ?? WebSocket;
    this.minDelay = options.minDelayMs ?? 500;
    this.maxDelay = options.maxDelayMs ?? 8000;
  }

  connect(): void {
    this.stopped = false;
    this.open();
  }

  send(message: ClientMessage): boolean {
    if (!this.ws || this.ws.readyState !== this.WS.OPEN) return false;
    this.ws.send(JSON.stringify(message));
    return true;
  }

  close(): void {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.ws?.close();
    this.ws = null;
  }

  /** Delay before the next reconnection attempt. */
  nextDelay(): number {
    return Math.min(this.maxDelay, this.minDelay * 2 ** Math.max(0, this.attempts - 1));
  }

  private open(): void {
    this.options.onStatus("connecting");
    const ws = new this.WS(this.options.url);
    this.ws = ws;
    ws.onopen = () => {
      this.attempts = 0;
      this.options.onStatus("open");
    };
    ws.onmessage = (message: MessageEvent) => {
      const event = typeof message.data === "string" ? parseServerEvent(message.data) : null;
      if (event) this.options.onEvent(event);
    };
    ws.onclose = () => {
      if (this.ws !== ws) return; // superseded
      this.ws = null;
      this.options.onStatus("closed");
      if (!this.stopped) this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    this.attempts += 1;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (!this.stopped) this.open();
    }, this.nextDelay());
  }
}
