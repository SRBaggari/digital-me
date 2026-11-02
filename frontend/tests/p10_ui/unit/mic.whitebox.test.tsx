import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MicrophoneError, explainMicError } from "../../../src/audio/microphone";
import { MicButton } from "../../../src/components/MicButton";
import { hearingStatusText } from "../../../src/components/VoicePanel";

describe("microphone internals", () => {
  it.each([
    ["NotAllowedError", "denied"],
    ["SecurityError", "denied"],
    ["NotFoundError", "unavailable"],
    ["NotReadableError", "unavailable"],
    ["AbortError", "unavailable"],
  ])("explainMicError(%s) -> %s", (name, reason) => {
    expect(explainMicError(new DOMException("x", name)).reason).toBe(reason);
  });

  it("keeps an existing MicrophoneError as is", () => {
    const error = new MicrophoneError("unsupported", "no audio");
    expect(explainMicError(error)).toBe(error);
  });

  it("MicButton is disabled while starting and announces its state", () => {
    const { rerender } = render(<MicButton status="starting" onToggle={vi.fn()} />);
    expect(screen.getByRole("button")).toBeDisabled();
    rerender(<MicButton status="on" onToggle={vi.fn()} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
    rerender(<MicButton status="off" onToggle={vi.fn()} disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it.each([
    ["loading", "base.en", "Loading speech recognition…"],
    ["ready", "small.en", "Speech recognition ready (small.en) · runs on this PC"],
    ["error: no model", "base.en", "Speech recognition problem: no model"],
    ["off", "base.en", "Speech recognition is off"],
  ])("hearingStatusText(%s)", (status, model, text) => {
    expect(hearingStatusText(status, model)).toBe(text);
  });
});
