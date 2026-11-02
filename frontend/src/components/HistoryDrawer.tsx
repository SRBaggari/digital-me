import { MessagesSquare, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import type { ConversationDTO } from "../api/protocol";
import type { Api } from "../api/rest";
import { relativeTime } from "../lib/format";

interface Props {
  open: boolean;
  api: Api;
  currentId: number | null;
  onClose: () => void;
  onOpenConversation: (id: number) => void;
  onDeletedCurrent: () => void;
}

export function HistoryDrawer({ open, api, currentId, onClose, onOpenConversation, onDeletedCurrent }: Props) {
  const [items, setItems] = useState<ConversationDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.conversations());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load history");
    }
  }, [api]);

  useEffect(() => {
    if (!open) return;
    setConfirming(null);
    void load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const remove = async (id: number) => {
    try {
      await api.deleteConversation(id);
      setItems((current) => current?.filter((c) => c.id !== id) ?? null);
      if (id === currentId) onDeletedCurrent();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete");
    } finally {
      setConfirming(null);
    }
  };

  const visible = items?.filter((c) => c.message_count > 0 || c.id === currentId) ?? [];

  return (
    <>
      <div className={`scrim ${open ? "scrim--open" : ""}`} onClick={onClose} aria-hidden />
      <aside className={`drawer ${open ? "drawer--open" : ""}`} aria-label="Conversation history" aria-hidden={!open} inert={!open}>
        <header className="drawer__header">
          <h2>Conversations</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close history">
            <X size={18} />
          </button>
        </header>
        {error && <p className="drawer__error">{error}</p>}
        {items && visible.length === 0 && (
          <div className="drawer__empty">
            <MessagesSquare size={28} aria-hidden />
            <p>No conversations yet.</p>
          </div>
        )}
        <ul className="drawer__list">
          {visible.map((conversation) => (
            <li key={conversation.id} className={`history-item ${conversation.id === currentId ? "history-item--current" : ""}`}>
              <button
                type="button"
                className="history-item__open"
                onClick={() => {
                  onOpenConversation(conversation.id);
                  onClose();
                }}
              >
                <span className="history-item__title">{conversation.title ?? "New conversation"}</span>
                <span className="history-item__meta">
                  {relativeTime(conversation.started_at)} · {conversation.message_count} messages
                </span>
              </button>
              {confirming === conversation.id ? (
                <span className="history-item__confirm">
                  <button type="button" className="text-button text-button--danger" onClick={() => void remove(conversation.id)}>
                    Delete
                  </button>
                  <button type="button" className="text-button" onClick={() => setConfirming(null)}>
                    Keep
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="icon-button icon-button--subtle"
                  aria-label={`Delete ${conversation.title ?? "conversation"}`}
                  onClick={() => setConfirming(conversation.id)}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </li>
          ))}
        </ul>
      </aside>
    </>
  );
}
