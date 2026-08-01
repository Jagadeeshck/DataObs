// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import {
  parseTimeRange,
  ProductContextProvider,
  timeRangeBounds,
  useProductContext,
} from "./context";
const identity = {
  subject: "user",
  permissions: [],
  tenants: [
    { id: "tenant-a", environments: ["prod", "stage"] },
    { id: "tenant-b", environments: ["dev"] },
  ],
};
describe("product context", () => {
  it("parses only supported ranges and computes explicit bounds", () => {
    expect(parseTimeRange("7d")).toBe("7d");
    expect(parseTimeRange("forever")).toBe("24h");
    expect(timeRangeBounds("1h", new Date("2026-01-01T01:00:00Z"))).toEqual({
      start: "2026-01-01T00:00:00.000Z",
      end: "2026-01-01T01:00:00.000Z",
    });
  });
  it("accepts only trusted tenant environments and invalidates on context or refresh changes", async () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ProductContextProvider initialContext={identity}>
        {children}
      </ProductContextProvider>
    );
    const { result } = renderHook(() => useProductContext(), { wrapper });
    await waitFor(() => expect(result.current.tenant).toBe("tenant-a"));
    const generation = result.current.refreshGeneration;
    act(() => result.current.setEnvironment("invalid"));
    expect(result.current.environment).toBe("prod");
    act(() => result.current.setTenant("tenant-b"));
    expect(result.current.environment).toBe("dev");
    expect(result.current.refreshGeneration).toBeGreaterThan(generation);
    const next = result.current.refreshGeneration;
    act(() => result.current.requestRefresh());
    expect(result.current.refreshGeneration).toBe(next + 1);
  });
});
