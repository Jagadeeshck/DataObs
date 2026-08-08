import { buildRoutePath } from "../app/routes";
import { investigationLink } from "../app/investigation";
import type { ActivityItem } from "./types";
export const activitySourcePath = (item: ActivityItem) =>
  item.routeId
    ? buildRoutePath(item.routeId, item.routeParameters ?? {})
    : undefined;
export const activityInvestigationPath = (
  item: ActivityItem,
  range: import("../state/context").TimeRange,
) =>
  item.entityType && item.entityId
    ? investigationLink(
        "investigation-workspace",
        {},
        {
          sourceRoute: "activity-center",
          entityType: item.entityType,
          entityId: item.entityId,
          timeRange: range,
          returnRoute: "/activity",
        },
      )
    : undefined;
