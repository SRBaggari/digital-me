import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MAX_INPUT_CHARS } from "../../../src/api/protocol";
import { Banner } from "../../../src/components/Banner";
import { Composer } from "../../../src/components/Composer";
import { MessageBubble } from "../../../src/components/MessageBubble";
import { StatusPill } from "../../../src/components/StatusPill";

function composer(props: Partial<Parameters<typeof Composer>[0]> = {}) {
  const onSend = vi.fn(() => true);
  const onStop = vi.fn();
  render(<Composer responding={false} connected onSend={onSend} onStop={onStop} placeholder="Message Sam…" {...props} />);
  return { onSend, onStop, input: screen.getByRole("textbox", { name: "Message" }) };
}

describe("Composer", () => {
  it("sends on Enter and clears the input", async () => {
    const { onSend, input } = composer();
    await userEvent.type(input, "Hello{Enter}");
    expect(onSend).toHaveBeenCalledWith("Hello");
    expect(input).toHaveValue("");
  });

  it("Shift+Enter inserts a new line", async () => {
    const { onSend, input } = composer();
    await userEvent.type(input, "a{Shift>}{Enter}{/Shift}b");
    expect(onSend).not.toHaveBeenCalled();
    expect(input).toHaveValue("a\nb");
  });

  it("does not send blank text", async () => {
    const { onSend, input } = composer();
    await userEvent.type(input, "   {Enter}");
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("keeps the text if sending fails", async () => {
    const { input } = composer({ onSend: vi.fn(() => false) });
    await userEvent.type(input, "Hello{Enter}");
    expect(input).toHaveValue("Hello");
  });

  it("cannot send while disconnected", async () => {
    const { onSend, input } = composer({ connected: false });
    expect(input).toHaveAttribute("placeholder", "Connecting…");
    await userEvent.type(input, "Hello{Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("shows a Stop button while responding and Esc stops", async () => {
    const { onStop, input } = composer({ responding: true });
    await userEvent.click(screen.getByRole("button", { name: "Stop reply" }));
    expect(onStop).toHaveBeenCalledTimes(1);
    await userEvent.type(input, "{Escape}");
    expect(onStop).toHaveBeenCalledTimes(2);
  });

  it("typing while responding offers Send again (to interrupt with a new message)", async () => {
    const { input } = composer({ responding: true });
    await userEvent.type(input, "wait");
    expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled();
  });

  it("blocks text over the length limit and shows the counter", async () => {
    const { onSend, input } = composer();
    await userEvent.click(input);
    await userEvent.paste("a".repeat(MAX_INPUT_CHARS + 1));
    expect(screen.getByText(`${MAX_INPUT_CHARS + 1}/${MAX_INPUT_CHARS}`)).toBeInTheDocument();
    await userEvent.type(input, "{Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });
});

describe("MessageBubble", () => {
  const base = { role: "assistant" as const, content: "Hi", emotion: "happy" as const, interrupted: false, createdAt: "2026-11-02T10:00:00", pending: false };

  it("shows non-neutral emotions", () => {
    render(<MessageBubble message={base} />);
    expect(screen.getByText("Happy")).toBeInTheDocument();
  });

  it("hides the neutral emotion label", () => {
    render(<MessageBubble message={{ ...base, emotion: "neutral" }} />);
    expect(screen.queryByText("Neutral")).not.toBeInTheDocument();
  });

  it("marks stopped replies", () => {
    render(<MessageBubble message={{ ...base, interrupted: true }} />);
    expect(screen.getByText("Stopped")).toBeInTheDocument();
  });

  it("marks streaming replies as busy", () => {
    render(<MessageBubble message={base} streaming />);
    expect(screen.getByRole("article")).toHaveAttribute("aria-busy", "true");
  });
});

describe("StatusPill", () => {
  it.each([
    ["idle", "Ready"],
    ["listening", "Listening"],
    ["thinking", "Thinking"],
    ["speaking", "Speaking"],
  ] as const)("%s shows %s", (state, label) => {
    render(<StatusPill state={state} />);
    expect(screen.getByRole("status")).toHaveTextContent(label);
  });
});

describe("Banner", () => {
  it("shows nothing when connected without errors", () => {
    const { container } = render(<Banner connection="open" everConnected error={null} onDismiss={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not warn during the very first connection attempt", () => {
    const { container } = render(<Banner connection="connecting" everConnected={false} error={null} onDismiss={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("warns when reconnecting", () => {
    render(<Banner connection="connecting" everConnected error={null} onDismiss={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Reconnecting");
  });

  it("explains model errors and can be dismissed", async () => {
    const onDismiss = vi.fn();
    render(<Banner connection="open" everConnected error={{ code: "llm_error", detail: "Is Ollama running?" }} onDismiss={onDismiss} />);
    expect(screen.getByRole("alert")).toHaveTextContent("The local model couldn't answer. Is Ollama running?");
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalled();
  });
});
