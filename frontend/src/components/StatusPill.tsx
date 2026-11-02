import { Brain, Ear, Sparkles, Volume2 } from "lucide-react";

import type { AvatarState } from "../api/protocol";
import { STATE_LABELS } from "../lib/format";

const ICONS = { idle: Sparkles, listening: Ear, thinking: Brain, speaking: Volume2 } as const;

export function StatusPill({ state }: { state: AvatarState }) {
  const Icon = ICONS[state];
  return (
    <div className={`status-pill status-pill--${state}`} role="status" aria-live="polite">
      <span className="status-pill__dot" aria-hidden />
      <Icon size={14} aria-hidden />
      <span>{STATE_LABELS[state]}</span>
    </div>
  );
}
