// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Evidence, shown } from "./Evidence";

describe("quality evidence states", () => {
  it("keeps measured zero distinct from missing evidence", () => {
    expect(shown(0)).toBe("0");
    expect(shown(null)).toBe("Not observed");
    expect(shown(undefined)).toBe("Not observed");
  });

  it("labels unavailable evidence without inventing metadata", () => {
    render(<Evidence status="unavailable">Runtime health</Evidence>);
    expect(screen.getByText("unavailable")).toBeTruthy();
    expect(screen.getByText(/No observation timestamp/)).toBeTruthy();
    expect(screen.getByText(/Source unavailable/)).toBeTruthy();
  });
});
