import { describe, expect, it } from "vitest";
import type { AxiosError } from "axios";
import { parseApiError } from "@/lib/api/errors";

function makeAxiosError(body: unknown): AxiosError<unknown> {
  return {
    isAxiosError: true,
    name: "AxiosError",
    message: "Request failed",
    config: {} as never,
    toJSON: () => ({}),
    response: { data: body, status: 400, statusText: "", headers: {}, config: {} as never },
  } as AxiosError<unknown>;
}

describe("parseApiError", () => {
  it("returns the server-supplied error envelope when present", () => {
    const err = makeAxiosError({
      error: { code: "PROJECT_NOT_FOUND", message: "Project not found" },
    });
    expect(parseApiError(err)).toEqual({
      code: "PROJECT_NOT_FOUND",
      message: "Project not found",
    });
  });

  it("preserves details when the server attaches them", () => {
    const err = makeAxiosError({
      error: {
        code: "VALIDATION_ERROR",
        message: "bad",
        details: { field: "title" },
      },
    });
    expect(parseApiError(err).details).toEqual({ field: "title" });
  });

  it("falls back to NETWORK_ERROR when the server didn't return an envelope", () => {
    const err = makeAxiosError(undefined);
    expect(parseApiError(err).code).toBe("NETWORK_ERROR");
  });

  it("falls back to NETWORK_ERROR for non-axios errors", () => {
    expect(parseApiError(new Error("boom")).code).toBe("NETWORK_ERROR");
  });
});
