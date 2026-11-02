import { useEffect, useState } from "react";

import type { AvatarState } from "../api/protocol";

interface Props {
  text: string;
  state: AvatarState;
  /** How long the last line stays after speech ends. */
  lingerMs?: number;
}

/** Subtitle line under the avatar, like captions on a video call. */
export function Caption({ text, state, lingerMs = 4000 }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!text) {
      setVisible(false);
      return;
    }
    if (state === "speaking") {
      setVisible(true);
      return;
    }
    const timer = setTimeout(() => setVisible(false), lingerMs);
    return () => clearTimeout(timer);
  }, [text, state, lingerMs]);

  return (
    <div className={`caption ${visible ? "caption--visible" : ""}`} aria-hidden={!visible}>
      <p key={text} className="caption__text">
        {text}
      </p>
    </div>
  );
}
