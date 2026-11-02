import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VoicePanel, speechStatusText } from "../../../src/components/VoicePanel";
import { VOICE } from "../../helpers";

describe("VoicePanel internals", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it.each([
    [undefined, "Voice engine is off"],
    ["off", "Voice engine is off"],
    ["loading", "Loading voice engine…"],
    ["ready", "Voice engine ready · runs on this PC"],
    ["error: no model", "Voice engine problem: no model"],
  ])("speechStatusText(%s)", (status, text) => {
    expect(speechStatusText(status)).toBe(text);
  });

  it("debounces speed changes and only saves the last value", () => {
    const onChange = vi.fn();
    render(<VoicePanel open voice={VOICE} error={null} onClose={() => {}} onChange={onChange} onPreview={vi.fn()} debounceMs={200} />);
    const slider = screen.getByRole("slider", { name: "Speaking speed" });
    fireEvent.change(slider, { target: { value: "1.2" } });
    act(() => vi.advanceTimersByTime(150));
    fireEvent.change(slider, { target: { value: "1.3" } });
    act(() => vi.advanceTimersByTime(199));
    expect(onChange).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ speed: 1.3 });
  });

  it("follows speed changes coming from the server", () => {
    const { rerender } = render(
      <VoicePanel open voice={VOICE} error={null} onClose={() => {}} onChange={vi.fn()} onPreview={vi.fn()} />,
    );
    rerender(
      <VoicePanel
        open
        voice={{ ...VOICE, settings: { ...VOICE.settings, speed: 1.5 } }}
        error={null}
        onClose={() => {}}
        onChange={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("1.50×")).toBeInTheDocument();
  });

  it("Escape closes only while open", () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <VoicePanel open={false} voice={VOICE} error={null} onClose={onClose} onChange={vi.fn()} onPreview={vi.fn()} />,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
    rerender(<VoicePanel open voice={VOICE} error={null} onClose={onClose} onChange={vi.fn()} onPreview={vi.fn()} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
