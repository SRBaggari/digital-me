import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Caption } from "../../../src/components/Caption";
import { EMOTION_HUES, Presence } from "../../../src/components/Presence";
import { useRelaxedEmotion } from "../../../src/components/Stage";
import { modelHealth } from "../../../src/components/TopBar";
import { STATUS_OK } from "../../helpers";

describe("component internals", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("Caption stays while speaking and hides after the linger time", () => {
    const { container, rerender } = render(<Caption text="Hello." state="speaking" lingerMs={1000} />);
    const caption = container.querySelector(".caption")!;
    expect(caption).toHaveClass("caption--visible");
    rerender(<Caption text="Hello." state="idle" lingerMs={1000} />);
    act(() => vi.advanceTimersByTime(999));
    expect(caption).toHaveClass("caption--visible");
    act(() => vi.advanceTimersByTime(1));
    expect(caption).not.toHaveClass("caption--visible");
  });

  it("Caption is hidden when there is no text", () => {
    const { container } = render(<Caption text="" state="speaking" />);
    expect(container.querySelector(".caption")).not.toHaveClass("caption--visible");
  });

  it("useRelaxedEmotion returns to neutral after idling", () => {
    const { result, rerender } = renderHook(({ state, emotion }) => useRelaxedEmotion(state, emotion, 500), {
      initialProps: { state: "speaking" as const, emotion: "happy" as const },
    });
    expect(result.current).toBe("happy");
    rerender({ state: "idle" as never, emotion: "happy" });
    act(() => vi.advanceTimersByTime(500));
    expect(result.current).toBe("neutral");
  });

  it("Presence exposes state and emotion and tints with the emotion hue", () => {
    render(<Presence state="thinking" emotion="sad" pulse={0} name="Sam" />);
    const el = screen.getByRole("img");
    expect(el).toHaveAttribute("data-state", "thinking");
    expect(el).toHaveAttribute("data-emotion", "sad");
    expect(el.style.getPropertyValue("--presence-hue")).toBe(EMOTION_HUES.sad);
  });

  it.each([
    [null, true, "down", "Server offline"],
    [null, false, "pending", "Checking…"],
    [{ ...STATUS_OK, llm: { reachable: false, model_available: false, detail: "" } }, false, "down", "Ollama not running"],
    [{ ...STATUS_OK, llm: { reachable: true, model_available: false, detail: "" } }, false, "warn", "Model not installed"],
    [STATUS_OK, false, "ok", "llama3.2:3b · on this PC"],
  ])("modelHealth branch %#", (status, unreachable, level, text) => {
    expect(modelHealth(status, unreachable)).toEqual({ level, text });
  });
});
