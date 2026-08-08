export const SEEN_KEY = "dataobs.activity.seen.v1",
  MAX_SEEN = 500,
  SEEN_TTL_MS = 86_400_000;
type Entry = { key: string; seenAt: number };
type Envelope = { context: string; entries: Entry[] };
export class ActivitySeenStore {
  constructor(
    private storage: Pick<
      Storage,
      "getItem" | "setItem" | "removeItem"
    > = sessionStorage,
    private now = () => Date.now(),
  ) {}
  read(context: string): Entry[] {
    try {
      const value = JSON.parse(
        this.storage.getItem(SEEN_KEY) ?? "null",
      ) as Envelope | null;
      if (
        !value ||
        value.context !== context ||
        !Array.isArray(value.entries)
      ) {
        this.clear();
        return [];
      }
      return value.entries
        .filter(
          (x) =>
            typeof x.key === "string" &&
            typeof x.seenAt === "number" &&
            this.now() - x.seenAt <= SEEN_TTL_MS,
        )
        .slice(-MAX_SEEN);
    } catch {
      this.clear();
      return [];
    }
  }
  mark(context: string, keys: readonly string[]) {
    const byKey = new Map(this.read(context).map((x) => [x.key, x]));
    keys.forEach((key) => byKey.set(key, { key, seenAt: this.now() }));
    const entries = [...byKey.values()].slice(-MAX_SEEN);
    this.storage.setItem(SEEN_KEY, JSON.stringify({ context, entries }));
    return entries;
  }
  clear() {
    this.storage.removeItem(SEEN_KEY);
  }
}
export const activityContextFingerprint = (
  tenant: string,
  environment: string,
) => `${tenant.length}:${tenant}|${environment.length}:${environment}`;
