import { describe, expect, it, vi } from "vitest";

// Mock the API barrel so the test does not load the heavy observability/transport
// import chain. ApiError is reproduced faithfully. `impl` is a mutable per-test
// handler; the mock calls through it so no eager rejected promise is ever stored
// (which would otherwise be flagged as an unhandled rejection by the runner).
const { state, MockApiError } = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number;
    requestId?: string;
    constructor(message: string, status: number, requestId?: string) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.requestId = requestId;
    }
  }
  const state: { impl: (...args: unknown[]) => Promise<unknown> } = {
    impl: async () => ({ items: [], next_cursor: null, data_status: "unknown", warnings: [] }),
  };
  return { state, MockApiError };
});
vi.mock("./index", () => ({
  api: { assets: (...args: unknown[]) => state.impl(...args) },
  ApiError: MockApiError,
}));

const { fetchCatalogPage } = await import("./catalogSearch");

const query = { tenant: "t", environment: "prod" } as const;

describe("catalog search client", () => {
  it("normalises a loaded page and carries evidence state through", async () => {
    state.impl = async () => ({
      items: [{ id: "a", name: "Asset A" }],
      next_cursor: "next",
      data_status: "partial",
      warnings: ["Scanner coverage incomplete"],
    });
    const result = await fetchCatalogPage(query);
    expect("page" in result).toBe(true);
    if (!("page" in result)) return;
    expect(result.page.items).toHaveLength(1);
    expect(result.page.nextCursor).toBe("next");
    expect(result.page.dataStatus).toBe("partial");
    expect(result.page.warnings).toEqual(["Scanner coverage incomplete"]);
  });

  it("returns a measured zero distinctly from an error", async () => {
    state.impl = async () => ({
      items: [],
      next_cursor: null,
      data_status: "complete",
      warnings: [],
    });
    const result = await fetchCatalogPage(query);
    expect("page" in result).toBe(true);
    if (!("page" in result)) return;
    expect(result.page.items).toEqual([]);
    expect(result.page.dataStatus).toBe("complete");
  });

  it("maps a missing endpoint (404) to a distinct unavailable message, not zero", async () => {
    state.impl = async () => {
      throw new MockApiError("not found", 404, "req-1");
    };
    const result = await fetchCatalogPage(query);
    expect("error" in result).toBe(true);
    if (!("error" in result)) return;
    expect(result.error.status).toBe(404);
    expect(result.error.requestId).toBe("req-1");
    expect(result.error.message).toMatch(/not available/i);
  });

  it("surfaces a generic transport failure as an error", async () => {
    state.impl = async () => {
      throw new MockApiError("boom", 500);
    };
    const result = await fetchCatalogPage(query);
    expect("error" in result && result.error.status).toBe(500);
  });

  it("re-throws on abort so the caller can ignore it", async () => {
    const controller = new AbortController();
    controller.abort();
    state.impl = async () => {
      throw new Error("aborted");
    };
    await expect(fetchCatalogPage(query, controller.signal)).rejects.toThrow();
  });
});
