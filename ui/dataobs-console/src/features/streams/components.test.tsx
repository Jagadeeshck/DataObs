// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DataStatusBanner, LagHeatmap, MetricCard } from "./components";

afterEach(cleanup);

describe("Stream 360 evidence semantics", () => {
  it("keeps measured zero distinct from missing latency", () => {
    const { rerender } = render(
      <MetricCard label="Latency" value={0} unit="ms" />,
    );
    expect(screen.getByText("0")).toBeTruthy();
    expect(screen.getByText("ms")).toBeTruthy();
    rerender(<MetricCard label="Latency" value={undefined} unit="ms" />);
    expect(screen.getByText("Unknown")).toBeTruthy();
    expect(screen.queryByText("ms")).toBeNull();
  });
  it("exposes zero, unknown and stale lag in the accessible domain view", () => {
    render(
      <LagHeatmap
        cells={[
          { topic: "orders", partition: 0, lag: 0 },
          { topic: "orders", partition: 1, lag: null },
          { topic: "orders", partition: 2, lag: 12, stale: true },
        ]}
        truncated
      />,
    );
    expect(
      screen.getByRole("gridcell", { name: "orders partition 0: lag 0" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("gridcell", { name: "orders partition 1: lag Unknown" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("gridcell", {
        name: "orders partition 2: lag 12, stale",
      }),
    ).toBeTruthy();
    expect(screen.getByText("Stale")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("truncated");
  });
  it.each(["not_configured", "stale", "partial", "unavailable", "unknown"])(
    "preserves %s without claiming healthy",
    (status) => {
      render(<DataStatusBanner status={status} />);
      expect(screen.getByRole("status").textContent).toBe(status);
      expect(screen.queryByText("healthy")).toBeNull();
    },
  );
});
