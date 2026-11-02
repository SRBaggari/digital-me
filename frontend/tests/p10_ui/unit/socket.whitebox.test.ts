import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DigitalMeSocket, defaultSocketUrl } from "../../../src/api/socket";
import { AsWebSocket, FakeWebSocket } from "../../helpers";

function make(overrides = {}) {
  const statuses: string[] = [];
  const events: unknown[] = [];
  const socket = new DigitalMeSocket({
    url: "ws://localhost/ws",
    onEvent: (e) => events.push(e),
    onStatus: (s) => statuses.push(s),
    WebSocketImpl: AsWebSocket,
    minDelayMs: 100,
    maxDelayMs: 800,
    ...overrides,
  });
  return { socket, statuses, events };
}

describe("DigitalMeSocket internals", () => {
  beforeEach(() => {
    FakeWebSocket.reset();
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("backs off exponentially and caps the delay", () => {
    const { socket } = make();
    socket.connect();
    const delays: number[] = [];
    for (let i = 0; i < 6; i++) {
      FakeWebSocket.latest().serverClose();
      delays.push(socket.nextDelay());
      vi.advanceTimersByTime(socket.nextDelay());
    }
    expect(delays).toEqual([100, 200, 400, 800, 800, 800]);
  });

  it("resets the backoff after a successful open", () => {
    const { socket } = make();
    socket.connect();
    FakeWebSocket.latest().serverClose();
    vi.advanceTimersByTime(100);
    FakeWebSocket.latest().serverClose();
    vi.advanceTimersByTime(200);
    FakeWebSocket.latest().serverOpen();
    FakeWebSocket.latest().serverClose();
    expect(socket.nextDelay()).toBe(100);
  });

  it("closes and ignores a superseded socket", () => {
    const { socket, statuses } = make();
    socket.connect();
    const first = FakeWebSocket.latest();
    statuses.length = 0;
    socket.connect(); // replaces the socket
    expect(first.readyState).toBe(FakeWebSocket.CLOSED);
    expect(statuses).toEqual(["connecting"]);
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("does not reconnect after close()", () => {
    const { socket } = make();
    socket.connect();
    socket.close();
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("close() cancels a pending reconnect timer", () => {
    const { socket } = make();
    socket.connect();
    FakeWebSocket.latest().serverClose();
    socket.close();
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("drops binary frames and unknown events", () => {
    const { socket, events } = make();
    socket.connect();
    const ws = FakeWebSocket.latest();
    ws.onmessage?.({ data: new ArrayBuffer(2) });
    ws.serverSend('{"type":"nope"}');
    expect(events).toEqual([]);
  });

  it("builds ws/wss URLs from the page location", () => {
    expect(defaultSocketUrl({ protocol: "http:", host: "localhost:8765" })).toBe("ws://localhost:8765/ws");
    expect(defaultSocketUrl({ protocol: "https:", host: "x" })).toBe("wss://x/ws");
  });
});
