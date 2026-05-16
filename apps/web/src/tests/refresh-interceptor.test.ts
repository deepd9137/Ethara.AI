import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// We need to test the module in isolation, so we mock axios before importing.
vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<typeof import("axios")>();
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => ({
        defaults: { headers: { common: {} } },
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
        post: vi.fn(),
      })),
    },
  };
});

describe("refreshAccessToken — race safety", () => {
  let refreshCallCount: number;
  let resolveRefresh: (token: string) => void;
  let mockPost: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    refreshCallCount = 0;

    // Re-import to get a fresh module (vitest isolates module state per test file,
    // but inflightRefresh is module-level — we reset it by re-importing with vi.resetModules)
    vi.resetModules();
    const axiosMock = await import("axios");
    mockPost = vi.fn(
      () =>
        new Promise<{ data: { access_token: string } }>((resolve) => {
          refreshCallCount++;
          resolveRefresh = (token) => resolve({ data: { access_token: token } });
        }),
    );
    // @ts-expect-error mocked
    axiosMock.default.create.mockReturnValue({
      defaults: { headers: { common: {} } },
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      post: mockPost,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("deduplicates concurrent refresh calls — only one POST /auth/refresh fires", async () => {
    const { refreshAccessToken } = await import("@/lib/api/client");

    // Fire 5 concurrent refresh attempts before the first resolves
    const promises = [
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
    ];

    // Resolve the single in-flight refresh
    resolveRefresh!("new-access-token");
    const results = await Promise.all(promises);

    expect(refreshCallCount).toBe(1);
    expect(results.every((r) => r === "new-access-token")).toBe(true);
  });

  it("allows a new refresh after the previous one settles", async () => {
    const { refreshAccessToken } = await import("@/lib/api/client");

    // First batch
    const first = refreshAccessToken();
    resolveRefresh!("token-1");
    await first;

    // Second call after first has settled — should trigger a new POST
    const second = refreshAccessToken();
    resolveRefresh!("token-2");
    const result = await second;

    expect(refreshCallCount).toBe(2);
    expect(result).toBe("token-2");
  });
});
