import type {
  StreamDetectorTemplate,
  StreamTemplateCatalog,
  StreamTemplateCategory,
} from "../api/streamTemplates";

/**
 * Pure presentation helpers for the pathway-authoring template picker.
 *
 * These helpers never fabricate templates and keep the catalog's honesty
 * semantics intact:
 * - `empty`      -> served catalog with zero templates (a measured empty list).
 * - `unknown`    -> requested a category the backend does not recognise.
 * - `unavailable`-> the catalog could not be loaded (fetch error / not yet loaded).
 * These are deliberately distinct states, never collapsed into "0".
 */

export type PickerStatus = "ready" | "empty" | "unknown" | "unavailable";

export interface PickerCategoryGroup {
  category: string;
  templates: StreamDetectorTemplate[];
}

export interface PickerViewModel {
  status: PickerStatus;
  categories: string[];
  groups: PickerCategoryGroup[];
  /** Templates whose capability tuple is unknown; surfaced, never silently hidden. */
  unsupported: StreamDetectorTemplate[];
  requestedCategory?: string;
}

const CATEGORY_ORDER: StreamTemplateCategory[] = [
  "freshness",
  "lag",
  "throughput",
];

function orderCategories(categories: string[]): string[] {
  const known = CATEGORY_ORDER.filter((category) =>
    categories.includes(category),
  );
  const extra = categories
    .filter(
      (category) =>
        !CATEGORY_ORDER.includes(category as StreamTemplateCategory),
    )
    .sort();
  return [...known, ...extra];
}

/**
 * Build the picker view model from a loaded catalog, or from `null`/`undefined`
 * when the catalog is unavailable (not loaded or failed).
 */
export function buildPicker(
  catalog: StreamTemplateCatalog | null | undefined,
): PickerViewModel {
  if (!catalog) {
    return {
      status: "unavailable",
      categories: [],
      groups: [],
      unsupported: [],
    };
  }

  const categories = orderCategories(catalog.categories ?? []);

  if (catalog.data_status === "unknown") {
    return {
      status: "unknown",
      categories,
      groups: [],
      unsupported: [],
      requestedCategory: catalog.requested_category,
    };
  }

  const items = catalog.items ?? [];
  const groups: PickerCategoryGroup[] = categories
    .map((category) => ({
      category,
      templates: items.filter((template) => template.category === category),
    }))
    .filter((group) => group.templates.length > 0);

  const unsupported = items.filter((template) => !template.applicable);

  return {
    status: items.length === 0 ? "empty" : "ready",
    categories,
    groups,
    unsupported,
  };
}
