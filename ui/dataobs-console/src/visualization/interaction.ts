export type VisualizationInteraction =
  | "hover"
  | "select"
  | "open"
  | "investigate"
  | "compare"
  | "zoom"
  | "brush";
export interface TimeSelection {
  from: number;
  to: number;
}
