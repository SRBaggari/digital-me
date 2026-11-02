import type { Emotion } from "../api/protocol";
import { clockTime, EMOTION_LABELS } from "../lib/format";
import type { ChatMessage } from "../state/chat";
import { EMOTION_HUES } from "./Presence";

interface Props {
  message: Pick<ChatMessage, "role" | "content" | "emotion" | "interrupted" | "createdAt" | "pending">;
  streaming?: boolean;
}

export function MessageBubble({ message, streaming = false }: Props) {
  const assistant = message.role === "assistant";
  const emotion: Emotion | null = assistant ? message.emotion : null;
  return (
    <article
      className={`bubble bubble--${message.role} ${message.pending ? "bubble--pending" : ""}`}
      aria-label={assistant ? "Reply" : "You said"}
      aria-busy={streaming || undefined}
    >
      <p className="bubble__content">
        {message.content}
        {streaming && <span className="bubble__caret" aria-hidden />}
      </p>
      <footer className="bubble__meta">
        {emotion && emotion !== "neutral" && (
          <span className="bubble__emotion" style={{ color: EMOTION_HUES[emotion] }}>
            <span className="bubble__emotion-dot" style={{ background: EMOTION_HUES[emotion] }} />
            {EMOTION_LABELS[emotion]}
          </span>
        )}
        {message.interrupted && <span className="bubble__tag">Stopped</span>}
        {!streaming && <time dateTime={message.createdAt}>{clockTime(message.createdAt)}</time>}
      </footer>
    </article>
  );
}
