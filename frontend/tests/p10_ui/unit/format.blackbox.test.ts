import { describe, expect, it } from "vitest";

import { AVATAR_STATES, EMOTIONS } from "../../../src/api/protocol";
import { EMOTION_LABELS, STATE_LABELS, clockTime, initials } from "../../../src/lib/format";

describe("format", () => {
  it.each([
    ["Sam", "SA"],
    ["sam lee", "SL"],
    ["  Ana  ", "AN"],
    ["", "?"],
    ["   ", "?"],
  ])("initials(%j) = %s", (name, expected) => {
    expect(initials(name)).toBe(expected);
  });

  it("has a label for every emotion and state", () => {
    for (const e of EMOTIONS) expect(EMOTION_LABELS[e]).toBeTruthy();
    for (const s of AVATAR_STATES) expect(STATE_LABELS[s]).toBeTruthy();
  });

  it("formats clock time", () => {
    expect(clockTime("2026-11-02T10:05:00")).toMatch(/10.05/);
  });
});
