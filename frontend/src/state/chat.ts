import { toEmotion, type AvatarState, type Emotion, type MessageDTO, type ServerEvent } from "../api/protocol";
import type { ConnectionStatus } from "../api/socket";

export interface ChatMessage {
  key: string;
  role: "user" | "assistant";
  content: string;
  emotion: Emotion | null;
  interrupted: boolean;
  createdAt: string;
  pending: boolean;
}

export interface ChatError {
  code: string;
  detail: string;
}

export interface ChatState {
  connection: ConnectionStatus;
  conversationId: number | null;
  messages: ChatMessage[];
  /** The assistant reply currently streaming in, if any. */
  draft: { text: string; emotion: Emotion } | null;
  avatarState: AvatarState;
  emotion: Emotion;
  /** Most recent complete sentence, shown as a subtitle on the stage. */
  caption: string;
  error: ChatError | null;
  localCounter: number;
}

export type ChatAction =
  | { type: "server"; event: ServerEvent }
  | { type: "connection"; status: ConnectionStatus }
  | { type: "send"; text: string; now: string }
  | { type: "dismiss_error" };

export const initialChatState: ChatState = {
  connection: "connecting",
  conversationId: null,
  messages: [],
  draft: null,
  avatarState: "idle",
  emotion: "neutral",
  caption: "",
  error: null,
  localCounter: 0,
};

export function fromDTO(message: MessageDTO): ChatMessage {
  return {
    key: `m${message.id}`,
    role: message.role,
    content: message.content,
    emotion: message.role === "assistant" ? toEmotion(message.emotion) : null,
    interrupted: message.interrupted,
    createdAt: message.created_at,
    pending: false,
  };
}

/** Codes for which the server never stored the user's message. */
const UNSAVED_INPUT_ERRORS = new Set(["invalid_input", "bad_request"]);

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "connection":
      return {
        ...state,
        connection: action.status,
        // A dropped connection ends the turn; the server stores what was said so far.
        ...(action.status === "closed" ? { draft: null, avatarState: "idle" as const } : {}),
      };
    case "dismiss_error":
      return { ...state, error: null };
    case "send": {
      const counter = state.localCounter + 1;
      const optimistic: ChatMessage = {
        key: `local${counter}`,
        role: "user",
        content: action.text,
        emotion: null,
        interrupted: false,
        createdAt: action.now,
        pending: true,
      };
      // Sending while a reply streams interrupts it; keep the partial text in the transcript.
      const messages = state.draft?.text
        ? [...state.messages, draftToMessage(state.draft, counter)]
        : state.messages;
      return {
        ...state,
        localCounter: counter,
        messages: [...messages, optimistic],
        draft: null,
        error: null,
      };
    }
    case "server":
      return applyServerEvent(state, action.event);
  }
}

function draftToMessage(draft: NonNullable<ChatState["draft"]>, counter: number): ChatMessage {
  return {
    key: `interrupted${counter}`,
    role: "assistant",
    content: draft.text.trim(),
    emotion: draft.emotion,
    interrupted: true,
    createdAt: new Date().toISOString(),
    pending: false,
  };
}

function applyServerEvent(state: ChatState, event: ServerEvent): ChatState {
  switch (event.type) {
    case "conversation":
      return {
        ...state,
        conversationId: event.conversation_id,
        messages: event.messages.map(fromDTO),
        draft: null,
        caption: "",
        emotion: "neutral",
      };
    case "state":
      return { ...state, avatarState: event.state };
    case "user_message": {
      const confirmed = fromDTO(event.message);
      const index = state.messages.findIndex((m) => m.pending && m.role === "user");
      const messages =
        index === -1
          ? [...state.messages, confirmed]
          : state.messages.map((m, i) => (i === index ? confirmed : m));
      return { ...state, messages };
    }
    case "emotion": {
      const emotion = toEmotion(event.emotion);
      return { ...state, emotion, draft: state.draft ? { ...state.draft, emotion } : state.draft };
    }
    case "assistant_delta":
      return {
        ...state,
        draft: { text: (state.draft?.text ?? "") + event.text, emotion: state.draft?.emotion ?? state.emotion },
      };
    case "sentence":
      return { ...state, caption: event.text };
    case "assistant_done":
      return { ...state, messages: [...state.messages, fromDTO(event.message)], draft: null };
    case "assistant_interrupted": {
      if (!state.draft?.text.trim()) return { ...state, draft: null };
      const counter = state.localCounter + 1;
      return {
        ...state,
        localCounter: counter,
        messages: [...state.messages, draftToMessage(state.draft, counter)],
        draft: null,
      };
    }
    case "error": {
      const messages = UNSAVED_INPUT_ERRORS.has(event.code)
        ? state.messages.filter((m) => !m.pending)
        : state.messages;
      return { ...state, messages, error: { code: event.code, detail: event.detail }, draft: null };
    }
  }
}

export function isResponding(state: ChatState): boolean {
  return state.avatarState === "thinking" || state.avatarState === "speaking" || state.draft !== null;
}
