import { describe, expect, it } from "vitest";

import { EMOTIONS, parseServerEvent, toEmotion } from "../../../src/api/protocol";

describe("protocol parsing internals", () => {
  it("rejects invalid JSON", () => {
    expect(parseServerEvent("{not json")).toBeNull();
  });

  it("rejects JSON primitives and null", () => {
    for (const raw of ["null", "1", '"state"', "true", "[]"]) expect(parseServerEvent(raw)).toBeNull();
  });

  it("rejects non-string type fields", () => {
    expect(parseServerEvent('{"type": 5}')).toBeNull();
  });

  it("toEmotion accepts every canonical emotion", () => {
    for (const e of EMOTIONS) expect(toEmotion(e)).toBe(e);
  });

  it("toEmotion falls back to neutral for anything else", () => {
    for (const v of [null, undefined, "", "HAPPY", 3, {}]) expect(toEmotion(v)).toBe("neutral");
  });
});
