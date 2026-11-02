import { request } from "./transport";

export type StreamTemplateCategory = "freshness" | "lag" | "throughput";

export type TemplateCapabilityStatus = "supported" | "unknown";

export interface StreamDetectorTemplateFields {
  resource_type: string;
  metric: string;
  method: string;
  direction: "high" | "low" | "both";
  baseline_window_seconds: number;
  evaluation_window_seconds: number;
  evaluation_interval_seconds: number;
  minimum_sample_count: number;
  sensitivity: number;
  seasonal_mode: string;
}

export interface StreamDetectorTemplate {
  template_id: string;
  title: string;
  category: StreamTemplateCategory;
  description: string;
  rationale: string;
  capability_status: TemplateCapabilityStatus;
  applicable: boolean;
  detector_fields: StreamDetectorTemplateFields;
}

export interface StreamTemplateCatalog {
  items: StreamDetectorTemplate[];
  categories: string[];
  // "descriptor" for a served list, "unknown" when an unrecognised category was
  // requested. Neither is a measured zero of running detectors.
  data_status: "descriptor" | "unknown";
  requested_category?: string;
}

const templatesPath = (environment: string, category?: string) => {
  const params = new URLSearchParams({ environment });
  if (category) params.set("category", category);
  return `/api/v1/stream-intelligence/templates?${params.toString()}`;
};

export const streamTemplatesApi = {
  list: (
    tenant: string,
    environment: string,
    category?: StreamTemplateCategory,
    signal?: AbortSignal,
  ) =>
    request<StreamTemplateCatalog>(templatesPath(environment, category), tenant, {
      environment,
      signal,
    }).then((result) => result.data),
};
