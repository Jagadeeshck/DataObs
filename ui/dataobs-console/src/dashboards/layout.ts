import { requireWidget } from "./registry";
import type { DashboardLayout, DashboardWidgetDefinition } from "./types";
export type LayoutAction =
  | "left"
  | "right"
  | "up"
  | "down"
  | "wider"
  | "narrower"
  | "taller"
  | "shorter";
export function adjustLayout(
  widget: DashboardWidgetDefinition,
  action: LayoutAction,
): DashboardLayout {
  const bounds = requireWidget(widget.type);
  const l = { ...widget.layout };
  if (action === "left") l.x = Math.max(0, l.x - 1);
  if (action === "right") l.x = Math.min(12 - l.width, l.x + 1);
  if (action === "up") l.y = Math.max(0, l.y - 1);
  if (action === "down") l.y++;
  if (action === "wider")
    l.width = Math.min(bounds.max.width, 12 - l.x, l.width + 1);
  if (action === "narrower") l.width = Math.max(bounds.min.width, l.width - 1);
  if (action === "taller") l.height = Math.min(bounds.max.height, l.height + 1);
  if (action === "shorter")
    l.height = Math.max(bounds.min.height, l.height - 1);
  return l;
}
export const responsiveLayout = (
  layout: DashboardLayout,
  columns: number,
): DashboardLayout =>
  columns < 6
    ? { ...layout, x: 0, width: columns }
    : {
        ...layout,
        x: Math.min(layout.x, columns - layout.width),
        width: Math.min(layout.width, columns),
      };
