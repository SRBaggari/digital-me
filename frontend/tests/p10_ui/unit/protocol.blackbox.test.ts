import { describe, expect, it } from "vitest";

import { parseServerEvent } from "../../../src/api/protocol";

describe("parseServerEvent", () => {
  it.each([
    '{"type":"state","state":"idle"}',
    '{"type":"assistant_delta","text":"hi"}',
    '{"type":"assistant_interrupted"}',
    '{"type":"error","code":"x","detail":"y"}',
  ])("accepts known event %s", (raw) => {
    expect(parseServerEvent(raw)).toEqual(JSON.parse(raw));
  });

  it("ignores unknown event types", () => {
    expect(parseServerEvent('{"type":"launch_rockets"}')).toBeNull();
  });

  it("ignores messages without a type", () => {
    expect(parseServerEvent('{"text":"hi"}')).toBeNull();
  });
});
