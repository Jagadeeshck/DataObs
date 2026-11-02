import { describe, expect, it } from "vitest";
import { buildPicker } from "./streamTemplatePicker";
import type {
  StreamDetectorTemplate,
  StreamTemplateCatalog,
} from "../api/streamTemplates";

const template = (
  overrides: Partial<StreamDetectorTemplate> = {},
): StreamDetectorTemplate => ({
  template_id: "lag_consumer_total",
  title: "Consumer total lag anomaly",
  category: "lag",
  description: "Detect abnormal growth in a consumer group's total lag.",
  rationale: "Robust z-score tolerates spiky lag.",
  capability_status: "supported",
  applicable: true,
  detector_fields: {
    resource_type: "consumer_group",
    metric: "total_lag",
    method: "robust_zscore",
    direction: "high",
    baseline_window_seconds: 86_400,
    evaluation_window_seconds: 1_800,
    evaluation_interval_seconds: 300,
    minimum_sample_count: 8,
    sensitivity: 4,
    seasonal_mode: "none",
  },
  ...overrides,
});

const catalog = (
  overrides: Partial<StreamTemplateCatalog> = {},
): StreamTemplateCatalog => ({
  items: [template()],
  categories: ["freshness", "lag", "throughput"],
  data_status: "descriptor",
  ...overrides,
});

describe("buildPicker", () => {
  it("groups templates by category in the authoring order", () => {
    const view = buildPicker(
      catalog({
        items: [
          template({ template_id: "t", category: "throughput" }),
          template({ template_id: "f", category: "freshness" }),
          template({ template_id: "l", category: "lag" }),
        ],
      }),
    );
    expect(view.status).toBe("ready");
    expect(view.groups.map((g) => g.category)).toEqual([
      "freshness",
      "lag",
      "throughput",
    ]);
  });

  it("surfaces unsupported templates instead of hiding them", () => {
    const view = buildPicker(
      catalog({
        items: [
          template(),
          template({
            template_id: "broken",
            applicable: false,
            capability_status: "unknown",
          }),
        ],
      }),
    );
    expect(view.unsupported.map((t) => t.template_id)).toEqual(["broken"]);
  });

  it("distinguishes a measured-empty catalog from unavailable", () => {
    expect(buildPicker(catalog({ items: [] })).status).toBe("empty");
    expect(buildPicker(null).status).toBe("unavailable");
    expect(buildPicker(undefined).status).toBe("unavailable");
  });

  it("reports an unknown requested category distinctly from empty", () => {
    const view = buildPicker(
      catalog({
        items: [],
        data_status: "unknown",
        requested_category: "bogus",
      }),
    );
    expect(view.status).toBe("unknown");
    expect(view.requestedCategory).toBe("bogus");
  });
});
