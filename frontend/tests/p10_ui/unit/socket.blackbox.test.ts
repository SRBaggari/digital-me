import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DigitalMeSocket } from "../../../src/api/socket";
import { AsWebSocket, FakeWebSocket } from "../../helpers";

describe("DigitalMeSocket", () => {
  beforeEach(() => {
    FakeWebSocket.reset();
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  function setup() {
    const statuses: string[] = [];
    const events: unknown[] = [];
    const socket = new DigitalMeSocket({
      url: "ws://localhost/ws",
      onEvent: (e) => events.push(e),
      onStatus: (s) => statuses.push(s),
      WebSocketImpl: AsWebSocket,
    });
    return { socket, statuses, events };
  }

  it("reports connecting then open", () => {
    const { socket, statuses } = setup();
    socket.connect();
    FakeWebSocket.latest().serverOpen();
    expect(statuses).toEqual(["connecting", "open"]);
  });

  it("delivers server events", () => {
    const { socket, events } = setup();
    socket.connect();
    FakeWebSocket.latest().serverSend({ type: "state", state: "thinking" });
    expect(events).toEqual([{ type: "state", state: "thinking" }]);
  });

  it("refuses to send before the connection is open", () => {
    const { socket } = setup();
    socket.connect();
    expect(socket.send({ type: "interrupt" })).toBe(false);
    expect(FakeWebSocket.latest().sent).toEqual([]);
  });

  it("sends JSON once open", () => {
    const { socket } = setup();
    socket.connect();
    FakeWebSocket.latest().serverOpen();
    expect(socket.send({ type: "user_message", text: "hi" })).toBe(true);
    expect(JSON.parse(FakeWebSocket.latest().sent[0])).toEqual({ type: "user_message", text: "hi" });
  });

  it("reconnects automatically after the server goes away", () => {
    const { socket, statuses } = setup();
    socket.connect();
    FakeWebSocket.latest().serverOpen();
    FakeWebSocket.latest().serverClose();
    expect(statuses.at(-1)).toBe("closed");
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1);
    expect(statuses.at(-1)).toBe("connecting");
  });

  it("send fails after close", () => {
    const { socket } = setup();
    socket.connect();
    FakeWebSocket.latest().serverOpen();
    socket.close();
    expect(socket.send({ type: "interrupt" })).toBe(false);
  });
});
