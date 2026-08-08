export const WATCHLIST_LIMIT = 25,
  WATCHLIST_KEY = "dataobs.operational-watchlist.v1";
export const watchlistEntityTypes = [
  "asset",
  "data-product",
  "monitor",
  "job",
  "run",
  "topic",
  "consumer-group",
  "pathway",
  "incident",
  "integration",
] as const;
export type WatchlistEntityType = (typeof watchlistEntityTypes)[number];
export interface WatchlistEntity {
  type: WatchlistEntityType;
  id: string;
  label: string;
}
export interface WatchlistEnvelope {
  contextFingerprint: string;
  items: WatchlistEntity[];
}
const valid = (x: WatchlistEntity) =>
  watchlistEntityTypes.includes(x.type) &&
  x.id.length > 0 &&
  x.id.length <= 512 &&
  x.label.length > 0 &&
  x.label.length <= 160;
export class WatchlistStore {
  constructor(
    private storage: Pick<
      Storage,
      "getItem" | "setItem" | "removeItem"
    > = sessionStorage,
  ) {}
  read(contextFingerprint: string): WatchlistEntity[] {
    try {
      const x = JSON.parse(
        this.storage.getItem(WATCHLIST_KEY) ?? "null",
      ) as WatchlistEnvelope | null;
      if (!x || x.contextFingerprint !== contextFingerprint) {
        this.clear();
        return [];
      }
      return x.items.filter(valid).slice(0, WATCHLIST_LIMIT);
    } catch {
      this.clear();
      return [];
    }
  }
  add(context: string, item: WatchlistEntity) {
    if (!valid(item)) throw new Error("Invalid canonical entity reference");
    const items = this.read(context);
    if (items.some((x) => x.type === item.type && x.id === item.id))
      return items;
    if (items.length >= WATCHLIST_LIMIT)
      throw new Error("Watchlist limit reached");
    const next = [...items, item];
    this.storage.setItem(
      WATCHLIST_KEY,
      JSON.stringify({ contextFingerprint: context, items: next }),
    );
    return next;
  }
  remove(context: string, type: WatchlistEntityType, id: string) {
    const next = this.read(context).filter(
      (x) => x.type !== type || x.id !== id,
    );
    this.storage.setItem(
      WATCHLIST_KEY,
      JSON.stringify({ contextFingerprint: context, items: next }),
    );
    return next;
  }
  clear() {
    this.storage.removeItem(WATCHLIST_KEY);
  }
}
export const contextFingerprint = (tenant: string, environment: string) =>
  `${tenant.length}:${tenant}|${environment.length}:${environment}`;
