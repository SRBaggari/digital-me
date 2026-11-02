import { useEffect, useState } from "react";

import type { AvatarState, Emotion } from "../api/protocol";
import { Caption } from "./Caption";
import { EMOTION_HUES, Presence } from "./Presence";
import { StatusPill } from "./StatusPill";

interface Props {
  name: string;
  state: AvatarState;
  emotion: Emotion;
  caption: string;
  pulse: number;
  /** Loudness of the voice being played, 0..1. */
  level?: () => number;
  /** After this long idle the expression relaxes back to neutral. */
  relaxAfterMs?: number;
}

export function useRelaxedEmotion(state: AvatarState, emotion: Emotion, relaxAfterMs: number): Emotion {
  const [shown, setShown] = useState<Emotion>(emotion);
  useEffect(() => {
    if (state !== "idle") {
      setShown(emotion);
      return;
    }
    setShown(emotion);
    const timer = setTimeout(() => setShown("neutral"), relaxAfterMs);
    return () => clearTimeout(timer);
  }, [state, emotion, relaxAfterMs]);
  return shown;
}

export function Stage({ name, state, emotion, caption, pulse, level, relaxAfterMs = 6000 }: Props) {
  const shown = useRelaxedEmotion(state, emotion, relaxAfterMs);
  return (
    <section
      className="stage"
      aria-label="Digital human"
      style={{ ["--stage-hue" as string]: EMOTION_HUES[shown] }}
    >
      <div className="stage__light" aria-hidden />
      <div className="stage__floor" aria-hidden />
      <div className="stage__status">
        <StatusPill state={state} />
      </div>
      <div className="stage__avatar">
        <Presence state={state} emotion={shown} pulse={pulse} name={name} level={level} />
      </div>
      <Caption text={caption} state={state} />
    </section>
  );
}
