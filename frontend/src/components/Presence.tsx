import type { CSSProperties } from "react";

import type { AvatarState, Emotion } from "../api/protocol";

/** Emotion palette shared with the stage lighting. Subtle on purpose. */
export const EMOTION_HUES: Record<Emotion, string> = {
  neutral: "#8ea2c8",
  happy: "#f2c27b",
  serious: "#7fa6ad",
  surprised: "#86d3f5",
  sad: "#8391d6",
  empathetic: "#e3a3c2",
};

interface Props {
  state: AvatarState;
  emotion: Emotion;
  /** Changes on every streamed chunk so the presence can react to speech rhythm. */
  pulse: number;
  name: string;
}

/**
 * Stand-in for the 3D avatar (Phase 4): a breathing presence that shows listening,
 * thinking and speaking, tinted by the current emotion.
 */
export function Presence({ state, emotion, pulse, name }: Props) {
  const style = { "--presence-hue": EMOTION_HUES[emotion] } as CSSProperties;
  return (
    <div
      className={`presence presence--${state}`}
      style={style}
      data-state={state}
      data-emotion={emotion}
      role="img"
      aria-label={`${name} is ${state === "idle" ? "ready" : state}`}
    >
      <div className="presence__halo" />
      <div className="presence__ring presence__ring--1" />
      <div className="presence__ring presence__ring--2" />
      <div className="presence__ring presence__ring--3" />
      <div className="presence__orbit" />
      <div className="presence__core">
        <div key={pulse} className="presence__beat" />
        <div className="presence__sheen" />
      </div>
    </div>
  );
}
