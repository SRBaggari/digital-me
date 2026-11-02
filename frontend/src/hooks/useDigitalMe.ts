import { useCallback, useEffect, useReducer, useRef } from "react";

import { MAX_INPUT_CHARS, type ClientMessage } from "../api/protocol";
import { DigitalMeSocket, defaultSocketUrl, type SocketOptions } from "../api/socket";
import { chatReducer, initialChatState, isResponding } from "../state/chat";

export type SocketFactory = (options: SocketOptions) => Pick<DigitalMeSocket, "connect" | "send" | "close">;

const defaultFactory: SocketFactory = (options) => new DigitalMeSocket(options);

/** Connects to the backend and exposes the conversation state plus the actions the UI needs. */
export function useDigitalMe(createSocket: SocketFactory = defaultFactory, url?: string) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const socketRef = useRef<ReturnType<SocketFactory> | null>(null);

  useEffect(() => {
    const socket = createSocket({
      url: url ?? defaultSocketUrl(),
      onEvent: (event) => dispatch({ type: "server", event }),
      onStatus: (status) => dispatch({ type: "connection", status }),
    });
    socketRef.current = socket;
    socket.connect();
    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [createSocket, url]);

  const send = useCallback((message: ClientMessage) => socketRef.current?.send(message) ?? false, []);

  const sendText = useCallback(
    (raw: string): boolean => {
      const text = raw.trim();
      if (!text || text.length > MAX_INPUT_CHARS) return false;
      if (!send({ type: "user_message", text })) return false;
      dispatch({ type: "send", text, now: new Date().toISOString() });
      return true;
    },
    [send],
  );

  return {
    state,
    responding: isResponding(state),
    sendText,
    interrupt: useCallback(() => send({ type: "interrupt" }), [send]),
    newConversation: useCallback(() => send({ type: "new_conversation" }), [send]),
    openConversation: useCallback(
      (id: number) => send({ type: "open_conversation", conversation_id: id }),
      [send],
    ),
    dismissError: useCallback(() => dispatch({ type: "dismiss_error" }), []),
  };
}

export type DigitalMe = ReturnType<typeof useDigitalMe>;
