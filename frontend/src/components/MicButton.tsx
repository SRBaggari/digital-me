import { Loader2, Mic, MicOff } from "lucide-react";
import { useRef } from "react";

import type { MicStatus } from "../state/chat";
import { useLevelVariable } from "./Presence";

interface Props {
  status: MicStatus;
  onToggle: () => void;
  disabled?: boolean;
  /** Loudness of the microphone, 0..1; drives the ring around the button. */
  level?: () => number;
}

const LABELS: Record<MicStatus, string> = {
  off: "Talk (turn microphone on)",
  starting: "Starting microphone…",
  on: "Stop listening (turn microphone off)",
};

export function MicButton({ status, onToggle, disabled = false, level }: Props) {
  const ref = useRef<HTMLButtonElement>(null);
  useLevelVariable(ref, status === "on", level);
  return (
    <button
      ref={ref}
      type="button"
      className={`mic-button mic-button--${status}`}
      onClick={onToggle}
      disabled={disabled || status === "starting"}
      aria-label={LABELS[status]}
      aria-pressed={status === "on"}
      title={LABELS[status]}
    >
      {status === "starting" ? <Loader2 size={18} className="spin" /> : status === "on" ? <Mic size={18} /> : <MicOff size={18} />}
    </button>
  );
}
