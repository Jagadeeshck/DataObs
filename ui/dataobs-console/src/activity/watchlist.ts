import type { ActivityItem } from "./types";
export function watchlistActivity(
  items: readonly ActivityItem[],
  watched: readonly { type: string; id: string }[],
) {
  const refs = new Set(watched.map((x) => `${x.type}\0${x.id}`));
  return items.filter(
    (x) =>
      x.entityType && x.entityId && refs.has(`${x.entityType}\0${x.entityId}`),
  );
}
