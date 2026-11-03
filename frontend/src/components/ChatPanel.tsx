import { useEffect, useRef, type ReactNode } from "react";

import type { AvatarState } from "../api/protocol";
import type { ChatState } from "../state/chat";
import { Composer, type ComposerHandle } from "./Composer";
import { MessageBubble } from "./MessageBubble";

export const SUGGESTIONS = [
  "Tell me a little about yourself.",
  "What do you enjoy doing?",
  "మీ గురించి కొంచెం చెప్పండి.", // "Tell me a little about yourself." in Telugu
];

interface Props {
  name: string;
  state: Pick<ChatState, "messages" | "draft" | "connection"> &
    Partial<Pick<ChatState, "mic" | "userSpeaking" | "transcribing">>;
  avatarState: AvatarState;
  responding: boolean;
  onSend: (text: string) => boolean;
  onStop: () => void;
  micButton?: ReactNode;
}

const STICK_THRESHOLD_PX = 120;

export function ChatPanel({ name, state, avatarState, responding, onSend, onStop, micButton }: Props) {
  const list = useRef<HTMLDivElement>(null);
  const composer = useRef<ComposerHandle>(null);
  const stick = useRef(true);
  const { messages, draft, userSpeaking = false, transcribing = false, mic = "off" } = state;
  const connected = state.connection === "open";

  useEffect(() => {
    const el = list.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [messages, draft?.text, avatarState, userSpeaking, transcribing]);

  useEffect(() => composer.current?.focus(), []);

  const onScroll = () => {
    const el = list.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_THRESHOLD_PX;
  };

  const empty = messages.length === 0 && !draft;
  const thinking = avatarState === "thinking" && !draft;

  return (
    <section className="chat" aria-label="Conversation">
      <div className="chat__list" ref={list} onScroll={onScroll} role="log" aria-live="polite" aria-relevant="additions">
        {empty && (
          <div className="chat__empty">
            <p className="chat__empty-title">Start a conversation with {name}</p>
            <p className="chat__empty-hint">
              Speak or type in English or Telugu · everything stays on this computer.
            </p>
            <div className="chips">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="chip"
                  disabled={!connected}
                  onClick={() => onSend(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.key} message={message} />
        ))}
        {draft && (
          <MessageBubble
            streaming
            message={{
              role: "assistant",
              content: draft.text,
              emotion: draft.emotion,
              interrupted: false,
              createdAt: "",
              pending: false,
            }}
          />
        )}
        {(userSpeaking || transcribing) && (
          <div className="hearing" role="status" aria-label={userSpeaking ? "Listening to you" : "Transcribing"}>
            <span className="hearing__bars" aria-hidden>
              <span />
              <span />
              <span />
              <span />
            </span>
            {userSpeaking ? "Listening…" : "Transcribing…"}
          </div>
        )}
        {thinking && !transcribing && (
          <div className="thinking" aria-label={`${name} is thinking`}>
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
      <div className="chat__composer">
        <Composer
          ref={composer}
          responding={responding}
          connected={connected}
          onSend={onSend}
          onStop={onStop}
          placeholder={mic === "on" ? `Talk to ${name}, or type…` : `Message ${name}…`}
          micButton={micButton}
        />
        <p className="chat__hint">
          {mic === "on" ? (
            <>Listening: just talk. Click the microphone to stop.</>
          ) : (
            <>
              <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> new line · <kbd>Esc</kbd> stop
            </>
          )}
        </p>
      </div>
    </section>
  );
}
