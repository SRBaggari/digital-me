import { AlertTriangle, WifiOff, X } from "lucide-react";

import type { ConnectionStatus } from "../api/socket";
import type { ChatError } from "../state/chat";

const FRIENDLY: Record<string, string> = {
  llm_error: "The local model couldn't answer.",
  invalid_input: "That message couldn't be sent.",
  bad_request: "That message couldn't be sent.",
  not_found: "That conversation no longer exists.",
  internal_error: "Something went wrong.",
};

interface Props {
  connection: ConnectionStatus;
  everConnected: boolean;
  error: ChatError | null;
  onDismiss: () => void;
}

export function Banner({ connection, everConnected, error, onDismiss }: Props) {
  if (connection === "closed" || (connection === "connecting" && everConnected)) {
    return (
      <div className="banner banner--warn" role="alert">
        <WifiOff size={16} aria-hidden />
        <span>Connection to Digital Me lost. Reconnecting…</span>
      </div>
    );
  }
  if (!error) return null;
  return (
    <div className="banner banner--error" role="alert">
      <AlertTriangle size={16} aria-hidden />
      <span>
        <strong>{FRIENDLY[error.code] ?? "Something went wrong."}</strong> {error.detail}
      </span>
      <button type="button" className="icon-button icon-button--subtle" onClick={onDismiss} aria-label="Dismiss">
        <X size={16} />
      </button>
    </div>
  );
}
