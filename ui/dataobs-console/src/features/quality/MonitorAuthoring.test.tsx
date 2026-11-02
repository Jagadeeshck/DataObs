// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const createMock = vi.fn();
const capabilitiesMock = vi.fn();

vi.mock("../../api/quality", () => ({
  qualityApi: {
    capabilities: (...args: unknown[]) => capabilitiesMock(...args),
    create: (...args: unknown[]) => createMock(...args),
  },
}));

vi.mock("../../state/context", () => ({
  useProductContext: () => ({ tenant: "acme", environment: "production" }),
}));

vi.mock("react-router-dom", () => ({
  Link: ({ children }: { children: unknown }) => children,
  useNavigate: () => vi.fn(),
}));

import { MonitorAuthoring } from "./MonitorAuthoring";

const capability = {
  monitor_type: "volume",
  display_name: "Volume",
  executable: true,
  supported_data_sources: ["postgresql"],
  threshold_modes: ["fixed", "learned"],
  target_requirements: [],
  required_parameters: [],
};

function fillMinimum() {
  fireEvent.change(screen.getByLabelText("Name"), {
    target: { value: "orders volume" },
  });
  fireEvent.change(screen.getByLabelText("Monitor type"), {
    target: { value: "volume" },
  });
  fireEvent.change(screen.getByLabelText("Source type"), {
    target: { value: "postgresql" },
  });
  fireEvent.change(screen.getByLabelText("Asset ID"), {
    target: { value: "warehouse.public.orders" },
  });
}

describe("MonitorAuthoring auto-detection toggle", () => {
  beforeEach(() => {
    createMock.mockReset();
    capabilitiesMock.mockReset();
    capabilitiesMock.mockResolvedValue({ data: { items: [capability] } });
    createMock.mockResolvedValue({ data: { id: "mon-1" } });
  });

  afterEach(() => cleanup());

  it("defaults to manual detection and sends detection_mode manual", async () => {
    render(<MonitorAuthoring />);
    await waitFor(() => screen.getByText("Volume"));
    fillMinimum();
    fireEvent.click(screen.getByText("Review definition"));
    fireEvent.click(screen.getByText("Create draft"));
    await waitFor(() => expect(createMock).toHaveBeenCalled());
    const payload = createMock.mock.calls[0][2];
    expect(payload.detection_mode).toBe("manual");
  });

  it("sends detection_mode auto when the toggle is enabled", async () => {
    render(<MonitorAuthoring />);
    await waitFor(() => screen.getByText("Volume"));
    fillMinimum();
    fireEvent.click(screen.getByLabelText(/Automatic detection/));
    fireEvent.click(screen.getByText("Review definition"));
    fireEvent.click(screen.getByText("Create draft"));
    await waitFor(() => expect(createMock).toHaveBeenCalled());
    const payload = createMock.mock.calls[0][2];
    expect(payload.detection_mode).toBe("auto");
  });

  it("explains the Enterprise ML requirement and honest unavailable state", async () => {
    render(<MonitorAuthoring />);
    await waitFor(() => screen.getByText("Volume"));
    expect(screen.getByText(/Elastic Enterprise ML license/)).toBeTruthy();
    expect(screen.getByText(/never silently treated as healthy/)).toBeTruthy();
  });
});
