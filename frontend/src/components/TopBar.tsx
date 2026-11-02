import { History, SquarePen } from "lucide-react";

import type { StatusDTO } from "../api/protocol";
import { initials } from "../lib/format";

interface Props {
  status: StatusDTO | null;
  serverUnreachable: boolean;
  onNewConversation: () => void;
  onOpenHistory: () => void;
  disabled: boolean;
}

export function modelHealth(status: StatusDTO | null, serverUnreachable: boolean) {
  if (serverUnreachable) return { level: "down", text: "Server offline" } as const;
  if (!status) return { level: "pending", text: "Checking…" } as const;
  if (!status.llm.reachable) return { level: "down", text: "Ollama not running" } as const;
  if (!status.llm.model_available) return { level: "warn", text: "Model not installed" } as const;
  return { level: "ok", text: `${status.model} · on this PC` } as const;
}

export function TopBar({ status, serverUnreachable, onNewConversation, onOpenHistory, disabled }: Props) {
  const name = status?.persona_name ?? "Digital Me";
  const health = modelHealth(status, serverUnreachable);
  return (
    <header className="topbar">
      <div className="identity">
        <div className="identity__avatar" aria-hidden>
          {initials(name)}
        </div>
        <div className="identity__text">
          <h1 className="identity__name">{name}</h1>
          <p className="identity__disclosure" title={status?.disclosure}>
            AI-generated digital human · not a live person
          </p>
        </div>
      </div>
      <div className="topbar__actions">
        <span
          className={`health health--${health.level}`}
          title={status?.llm.detail || health.text}
          data-testid="model-health"
        >
          <span className="health__dot" aria-hidden />
          {health.text}
        </span>
        <button type="button" className="icon-button" onClick={onOpenHistory} aria-label="Conversation history">
          <History size={18} />
        </button>
        <button
          type="button"
          className="icon-button"
          onClick={onNewConversation}
          aria-label="New conversation"
          disabled={disabled}
        >
          <SquarePen size={18} />
        </button>
      </div>
    </header>
  );
}
