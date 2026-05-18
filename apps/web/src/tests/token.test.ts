import { afterEach, describe, expect, it } from "vitest";
import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/auth/token";

describe("access token module — in-memory storage", () => {
  afterEach(() => {
    clearAccessToken();
  });

  it("starts null on a fresh module", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("returns the value most recently set", () => {
    setAccessToken("abc.def.ghi");
    expect(getAccessToken()).toBe("abc.def.ghi");

    setAccessToken("xyz");
    expect(getAccessToken()).toBe("xyz");
  });

  it("clears back to null", () => {
    setAccessToken("something");
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });
});
