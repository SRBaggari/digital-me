import { ArrowUp, Square } from "lucide-react";
import { forwardRef, useImperativeHandle, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";

import { MAX_INPUT_CHARS } from "../api/protocol";

interface Props {
  responding: boolean;
  connected: boolean;
  onSend: (text: string) => boolean;
  onStop: () => void;
  placeholder: string;
}

export interface ComposerHandle {
  focus: () => void;
  setText: (text: string) => void;
}

const MAX_HEIGHT = 180;
const COUNTER_FROM = MAX_INPUT_CHARS - 500;

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  { responding, connected, onSend, onStop, placeholder },
  ref,
) {
  const [text, setText] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => area.current?.focus(),
    setText: (value: string) => {
      setText(value);
      area.current?.focus();
    },
  }));

  useLayoutEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [text]);

  const tooLong = text.length > MAX_INPUT_CHARS;
  const canSend = connected && text.trim().length > 0 && !tooLong;

  const submit = () => {
    if (canSend && onSend(text)) setText("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    } else if (event.key === "Escape" && responding) {
      event.preventDefault();
      onStop();
    }
  };

  return (
    <form
      className={`composer ${responding ? "composer--responding" : ""}`}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        ref={area}
        className="composer__input"
        value={text}
        rows={1}
        placeholder={connected ? placeholder : "Connecting…"}
        aria-label="Message"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
      />
      <div className="composer__side">
        {text.length >= COUNTER_FROM && (
          <span className={`composer__count ${tooLong ? "composer__count--over" : ""}`}>
            {text.length}/{MAX_INPUT_CHARS}
          </span>
        )}
        {responding && !text.trim() ? (
          <button type="button" className="send-button send-button--stop" onClick={onStop} aria-label="Stop reply">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button type="submit" className="send-button" disabled={!canSend} aria-label="Send message">
            <ArrowUp size={18} />
          </button>
        )}
      </div>
    </form>
  );
});
