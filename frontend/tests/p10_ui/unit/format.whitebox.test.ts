import { describe, expect, it } from "vitest";

import { clockTime, initials, relativeTime } from "../../../src/lib/format";

const NOW = new Date("2026-11-02T12:00:00Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();

describe("format internals: thresholds", () => {
  it.each([
    [59_999, "just now"],
    [60_000, "1 min ago"],
    [3_599_999, "59 min ago"],
    [3_600_000, "1 h ago"],
    [86_399_999, "23 h ago"],
    [86_400_000, "yesterday"],
    [172_799_999, "yesterday"],
  ])("relativeTime(%i ms ago) = %s", (ms, expected) => {
    expect(relativeTime(ago(ms), NOW)).toBe(expected);
  });

  it("falls back to a date after two days", () => {
    expect(relativeTime(ago(3 * 86_400_000), NOW)).toMatch(/2026/);
  });

  it("returns empty strings for invalid dates", () => {
    expect(relativeTime("nope", NOW)).toBe("");
    expect(clockTime("nope")).toBe("");
  });

  it("initials uses first and last word", () => {
    expect(initials("Mary Jane Watson")).toBe("MW");
  });
});
