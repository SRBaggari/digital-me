import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createApi } from "../../../src/api/rest";
import { DigitalMeSocket } from "../../../src/api/socket";
import { useDigitalMe } from "../../../src/hooks/useDigitalMe";
import { useStatus } from "../../../src/hooks/useStatus";
import { AsWebSocket, FakeWebSocket, STATUS_OK, controllableSocket, fakeApi } from "../../helpers";

describe("useDigitalMe wiring", () => {
  it("does not add an optimistic message when the socket refuses to send", () => {
    const socket = controllableSocket();
    const { result } = renderHook(() => useDigitalMe(socket.factory, "ws://x"));
    let accepted = true;
    act(() => {
      accepted = result.current.sendText("hello");
    });
    expect(accepted).toBe(false);
    expect(result.current.state.messages).toEqual([]);
  });

  it("trims text and rejects blank or oversize messages before sending", () => {
    const socket = controllableSocket();
    const { result } = renderHook(() => useDigitalMe(socket.factory, "ws://x"));
    act(() => socket.open());
    act(() => {
      result.current.sendText("   ");
      result.current.sendText("x".repeat(4001));
      result.current.sendText("  hi  ");
    });
    expect(socket.sent).toEqual([{ type: "user_message", text: "hi" }]);
  });

  it("closes the socket on unmount", () => {
    const close = vi.fn();
    const { unmount } = renderHook(() =>
      useDigitalMe(() => ({ connect: () => {}, send: () => true, sendBinary: () => true, close }), "ws://x"),
    );
    unmount();
    expect(close).toHaveBeenCalled();
  });

  it("works end to end with the real socket class over a fake transport", () => {
    FakeWebSocket.reset();
    const factory = (options: ConstructorParameters<typeof DigitalMeSocket>[0]) =>
      new DigitalMeSocket({ ...options, WebSocketImpl: AsWebSocket });
    const { result } = renderHook(() => useDigitalMe(factory, "ws://x"));
    const ws = FakeWebSocket.latest();
    act(() => ws.serverOpen());
    expect(result.current.state.connection).toBe("open");
    act(() => ws.serverSend({ type: "conversation", conversation_id: 3, messages: [] }));
    act(() => {
      result.current.sendText("hey");
    });
    expect(JSON.parse(ws.sent[0])).toEqual({ type: "user_message", text: "hey" });
    expect(result.current.state.conversationId).toBe(3);
  });
});

describe("useStatus polling", () => {
  // Only intervals are faked: React's async act() needs a real setTimeout.
  beforeEach(() => vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] }));
  afterEach(() => vi.useRealTimers());

  it("polls quickly while unhealthy and slowly once healthy", async () => {
    let healthy = false;
    const status = vi.fn(async () =>
      healthy ? STATUS_OK : { ...STATUS_OK, llm: { reachable: false, model_available: false, detail: "" } },
    );
    const api = fakeApi({ status }); // must be stable, as App memoizes it
    const { result } = renderHook(() => useStatus(api, 10_000, 1_000));
    await act(async () => {});
    expect(result.current.healthy).toBe(false);
    healthy = true;
    await act(async () => vi.advanceTimersByTime(1_000));
    await act(async () => {});
    expect(result.current.healthy).toBe(true);
    const calls = status.mock.calls.length;
    await act(async () => vi.advanceTimersByTime(5_000));
    expect(status.mock.calls.length).toBe(calls);
  });
});

describe("REST client", () => {
  it("parses JSON, handles 204 and surfaces server error details", async () => {
    const fetchImpl = vi.fn(async (path: string, init?: RequestInit) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      if (path === "/api/status") return Response.json(STATUS_OK);
      return Response.json({ detail: "Conversation not found" }, { status: 404 });
    }) as unknown as typeof fetch;
    const api = createApi(fetchImpl);
    await expect(api.status()).resolves.toEqual(STATUS_OK);
    await expect(api.deleteConversation(1)).resolves.toBeUndefined();
    await expect(api.conversations()).rejects.toEqual(new ApiError(404, "Conversation not found"));
  });

  it("falls back to status text when the error body is not JSON", async () => {
    const fetchImpl = (async () => new Response("oops", { status: 500, statusText: "Server Error" })) as typeof fetch;
    await expect(createApi(fetchImpl).status()).rejects.toThrow("Server Error");
  });
});
