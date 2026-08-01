// @vitest-environment jsdom
import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAbortableRequest } from "./useAbortableRequest";
import { usePermission } from "./usePermission";
import { useTenantReset } from "./useTenantReset";

describe("shared request hooks", () => {
  it("aborts an obsolete request", () => {
    const signals: AbortSignal[] = [];
    const { result } = renderHook(() => useAbortableRequest());
    act(() => {
      void result.current(async (s) => {
        signals.push(s);
        return 1;
      });
      void result.current(async (s) => {
        signals.push(s);
        return 2;
      });
    });
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });
  it("checks explicit permissions", () => {
    const { result } = renderHook(() =>
      usePermission(["asset:read"], "asset:read"),
    );
    expect(result.current).toBe(true);
  });
  it("resets only when tenant context changes", () => {
    const reset = vi.fn();
    const { rerender } = renderHook(
      ({ tenant }) => useTenantReset(tenant, "test", reset),
      { initialProps: { tenant: "a" } },
    );
    expect(reset).not.toHaveBeenCalled();
    rerender({ tenant: "b" });
    expect(reset).toHaveBeenCalledOnce();
  });
});
