export interface QueryDescriptor<T> {
  providerId: string;
  timeBucket: string;
  filters: Record<string, string>;
  refreshGeneration: number;
  load: (signal: AbortSignal) => Promise<T>;
}
const keyFor = (q: QueryDescriptor<unknown>) =>
  JSON.stringify([
    q.providerId,
    q.timeBucket,
    Object.entries(q.filters).sort(),
    q.refreshGeneration,
  ]);
export class DashboardQueryCoordinator {
  private generation = 0;
  private controller = new AbortController();
  private requests = new Map<string, Promise<unknown>>();
  dedupeCount = 0;
  switchContext() {
    this.generation++;
    this.controller.abort();
    this.controller = new AbortController();
    this.requests.clear();
  }
  query<T>(descriptor: QueryDescriptor<T>): Promise<T> {
    const generation = this.generation,
      key = keyFor(descriptor);
    const found = this.requests.get(key) as Promise<T> | undefined;
    if (found) {
      this.dedupeCount++;
      return found;
    }
    const pending = descriptor.load(this.controller.signal).then((value) => {
      if (generation !== this.generation)
        throw new DOMException("Stale dashboard response", "AbortError");
      return value;
    });
    this.requests.set(key, pending);
    return pending;
  }
  clearRefresh() {
    this.requests.clear();
  }
}
