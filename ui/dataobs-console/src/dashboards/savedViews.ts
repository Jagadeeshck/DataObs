import { dashboardTemplate } from "./templates";
import { dashboardWidgetTypes, type DashboardDefinition } from "./types";
export const SAVED_VIEW_SCHEMA_VERSION = 1,
  MAX_SAVED_VIEWS = 20,
  MAX_WIDGETS = 20,
  MAX_VIEW_NAME = 80;
export const SAVED_VIEWS_KEY = "dataobs.safe-dashboard-views.v1";
export interface SafeSavedView extends DashboardDefinition {
  owner: "private";
  modifiedAt: string;
}
export interface SavedViewsEnvelope {
  schemaVersion: 1;
  views: SafeSavedView[];
}
const safeName = (name: string) =>
  name.trim().length > 0 &&
  name.trim().length <= MAX_VIEW_NAME &&
  !/[<>]/.test(name) &&
  ![...name].some((character) => character.charCodeAt(0) < 32);
export function parseSavedViews(raw: string | null): SavedViewsEnvelope {
  if (!raw) return { schemaVersion: 1, views: [] };
  try {
    const data = JSON.parse(raw) as Partial<SavedViewsEnvelope>;
    if (data.schemaVersion !== 1 || !Array.isArray(data.views))
      return { schemaVersion: 1, views: [] };
    const views = data.views
      .slice(0, MAX_SAVED_VIEWS)
      .filter(
        (view): view is SafeSavedView =>
          !!view &&
          view.owner === "private" &&
          safeName(view.title) &&
          typeof view.id === "string" &&
          /^private-[a-z0-9-]+$/.test(view.id) &&
          Array.isArray(view.widgets) &&
          view.widgets.length <= MAX_WIDGETS &&
          view.widgets.every(
            (w) =>
              dashboardWidgetTypes.includes(w.type) &&
              Object.keys(w.config ?? {}).length === 0,
          ),
      );
    return { schemaVersion: 1, views };
  } catch {
    return { schemaVersion: 1, views: [] };
  }
}
export function loadSavedViews(
  storage: Pick<Storage, "getItem"> = localStorage,
) {
  return parseSavedViews(storage.getItem(SAVED_VIEWS_KEY));
}
export function saveViews(
  envelope: SavedViewsEnvelope,
  storage: Pick<Storage, "setItem"> = localStorage,
) {
  storage.setItem(SAVED_VIEWS_KEY, JSON.stringify(envelope));
}
export function cloneTemplate(
  templateId: string,
  name: string,
  now = new Date(),
): SafeSavedView {
  const source = dashboardTemplate(templateId);
  if (!source) throw new Error("Unknown dashboard template");
  if (!safeName(name))
    throw new Error("View name must be 1–80 safe characters");
  return {
    ...structuredClone(source),
    id: `private-${crypto.randomUUID()}`,
    owner: "private",
    templateId,
    title: name.trim(),
    modifiedAt: now.toISOString(),
  };
}
export function resetSavedView(view: SafeSavedView): SafeSavedView {
  const source = dashboardTemplate(view.templateId ?? "");
  if (!source) throw new Error("Template is unavailable");
  return {
    ...structuredClone(source),
    id: view.id,
    owner: "private",
    templateId: source.id,
    title: view.title,
    modifiedAt: new Date().toISOString(),
  };
}
export function upsertSavedView(
  envelope: SavedViewsEnvelope,
  view: SafeSavedView,
) {
  const views = envelope.views.filter((x) => x.id !== view.id);
  if (views.length >= MAX_SAVED_VIEWS)
    throw new Error("Maximum private view count reached");
  return { schemaVersion: 1 as const, views: [...views, view] };
}
