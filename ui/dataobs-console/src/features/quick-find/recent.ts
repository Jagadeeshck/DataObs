export type RecentItem = {
  entityType: string;
  label: string;
  route: string;
  lastViewed: number;
  tenant: string;
  environment: string;
};
const key = "dataobs.console.recent.v1";
const MAX_ITEMS = 12;
const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;
export function readRecent(tenant: string, environment: string): RecentItem[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(key) ?? "[]") as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is RecentItem =>
          typeof item === "object" &&
          item !== null &&
          (item as RecentItem).tenant === tenant &&
          (item as RecentItem).environment === environment &&
          typeof (item as RecentItem).route === "string" &&
          (item as RecentItem).route.startsWith("/") &&
          Date.now() - (item as RecentItem).lastViewed <= MAX_AGE_MS,
      )
      .slice(0, MAX_ITEMS);
  } catch {
    return [];
  }
}
export function recordRecent(item: RecentItem) {
  const existing = readAll().filter(
    (candidate) =>
      !(
        candidate.tenant === item.tenant &&
        candidate.environment === item.environment &&
        candidate.route === item.route
      ),
  );
  sessionStorage.setItem(
    key,
    JSON.stringify(
      [item, ...existing]
        .sort((a, b) => b.lastViewed - a.lastViewed)
        .slice(0, MAX_ITEMS * 4),
    ),
  );
}
function readAll(): RecentItem[] {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}
export function clearRecentScope(tenant: string, environment: string) {
  sessionStorage.setItem(
    key,
    JSON.stringify(
      readAll().filter(
        (item) => !(item.tenant === tenant && item.environment === environment),
      ),
    ),
  );
}
