// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HealthBadge, MetricCard } from "./Evidence";
describe("evidence components", () => {
  it("preserves measured zero and separates missing evidence", () => {
    const { rerender } = render(<MetricCard label="Incidents" value={0} />);
    expect(screen.getByText("0")).toBeTruthy();
    rerender(<MetricCard label="Incidents" value={undefined} />);
    expect(screen.getByText("Unknown")).toBeTruthy();
  });
  it("labels partial evidence textually", () => {
    render(<HealthBadge state="partial" />);
    expect(screen.getByLabelText("Evidence state: partial")).toBeTruthy();
  });
});
