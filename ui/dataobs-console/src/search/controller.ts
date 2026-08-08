import { canSearch } from "./registry";
import { deduplicate, rankResults } from "./ranking";
import type {
  ProviderOutcome,
  SearchContext,
  SearchProvider,
  SearchSnapshot,
} from "./types";
export const SEARCH_DEADLINE_MS = 2_000,
  MAX_TOTAL_RESULTS = 25;
export class SearchController {
  private generation = 0;
  private aborter?: AbortController;
  constructor(private providers: readonly SearchProvider[]) {}
  cancel() {
    this.generation++;
    this.aborter?.abort();
  }
  async search(
    query: string,
    context: SearchContext,
    onUpdate?: (s: SearchSnapshot) => void,
  ): Promise<SearchSnapshot> {
    this.cancel();
    const generation = this.generation;
    const aborter = new AbortController();
    this.aborter = aborter;
    const eligible = this.providers
      .filter(
        (p) =>
          canSearch(p, context) && query.trim().length >= p.minimumQueryLength,
      )
      .slice(0, 10);
    const outcomes: ProviderOutcome[] = eligible.map((p) => ({
      providerId: p.id,
      label: p.label,
      status: "pending",
      resultCount: 0,
      durationBucket: "fast",
    }));
    const results = [] as SearchSnapshot["results"];
    const emit = (searching: boolean) => {
      const snapshot = {
        generation,
        searching,
        results: rankResults(deduplicate(results)).slice(0, MAX_TOTAL_RESULTS),
        providers: [...outcomes],
      };
      if (generation === this.generation) onUpdate?.(snapshot);
      return snapshot;
    };
    emit(true);
    const deadline = setTimeout(
      () => aborter.abort("deadline"),
      SEARCH_DEADLINE_MS,
    );
    await Promise.all(
      eligible.map(async (provider, index) => {
        const started = performance.now();
        const child = new AbortController();
        const cancel = () => child.abort("deadline");
        aborter.signal.addEventListener("abort", cancel, { once: true });
        const timeout = setTimeout(
          () => child.abort("timeout"),
          provider.timeoutMs,
        );
        try {
          const response = await provider.search(
            { query: query.trim(), context, limit: provider.maximumResults },
            child.signal,
          );
          if (generation !== this.generation) return;
          const items = response.results
            .slice(0, provider.maximumResults)
            .filter(
              (r) =>
                !r.requiredPermission ||
                context.permissions.includes(r.requiredPermission),
            );
          results.push(...items);
          outcomes[index] = {
            ...outcomes[index],
            status: items.length ? "complete" : "empty",
            resultCount: items.length,
            requestId: response.requestId,
          };
        } catch (error) {
          const status = child.signal.aborted
            ? aborter.signal.aborted
              ? "cancelled"
              : "timed_out"
            : (error as { status?: number }).status === 429
              ? "rate_limited"
              : "failed";
          outcomes[index] = { ...outcomes[index], status };
        } finally {
          clearTimeout(timeout);
          aborter.signal.removeEventListener("abort", cancel);
          const ms = performance.now() - started;
          outcomes[index].durationBucket =
            ms < 250 ? "fast" : ms < 1000 ? "normal" : "slow";
          emit(true);
        }
      }),
    );
    clearTimeout(deadline);
    return emit(false);
  }
}
