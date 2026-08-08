import {
  INVESTIGATION_LIMITS,
  type InvestigationProvider,
  type InvestigationRequest,
  type InvestigationSnapshot,
  type ProviderResult,
  type ProviderStatus,
} from "./types";
import { normaliseRelated, normaliseTimeline } from "./timeline";

export class InvestigationController {
  private controller?: AbortController;
  private generation = 0;
  constructor(private readonly providers: readonly InvestigationProvider[]) {}
  cancel() {
    this.controller?.abort();
  }
  async collect(
    request: Omit<InvestigationRequest, "generation">,
    publish: (snapshot: InvestigationSnapshot) => void,
  ) {
    this.cancel();
    const controller = new AbortController();
    this.controller = controller;
    const generation = ++this.generation;
    const eligible = this.providers.filter(
      (p) =>
        p.supports.includes(request.anchor.entityType) &&
        p.isAvailable({ ...request, generation }),
    );
    const statuses: ProviderStatus[] = this.providers
      .filter((p) => !p.supports.includes(request.anchor.entityType))
      .map((p) => ({ providerId: p.id, outcome: "unsupported", count: 0 }));
    let evidence: ProviderResult["evidence"] = [];
    let related: NonNullable<ProviderResult["related"]> = [];
    const emit = (loading: boolean) => {
      if (generation === this.generation && !controller.signal.aborted)
        publish({
          generation,
          loading,
          evidence: normaliseTimeline(evidence),
          related: normaliseRelated(related),
          providers: [...statuses],
        });
    };
    emit(true);
    const deadline = window.setTimeout(
      () => controller.abort("deadline"),
      INVESTIGATION_LIMITS.deadlineMs,
    );
    await Promise.all(
      eligible.map(async (provider) => {
        if (
          provider.requiredPermission &&
          !request.permissions.includes(provider.requiredPermission)
        ) {
          statuses.push({
            providerId: provider.id,
            outcome: "permission_denied",
            count: 0,
          });
          emit(true);
          return;
        }
        const local = new AbortController();
        const abort = () => local.abort();
        controller.signal.addEventListener("abort", abort, { once: true });
        const timer = window.setTimeout(
          () => local.abort("timeout"),
          provider.timeoutMs,
        );
        try {
          const result = await provider.collect(
            { ...request, generation },
            local.signal,
          );
          if (generation !== this.generation || controller.signal.aborted)
            return;
          const items = result.evidence.slice(0, provider.maximumEvents);
          evidence = evidence.concat(items);
          related = related.concat(result.related ?? []);
          statuses.push({
            providerId: provider.id,
            outcome:
              result.outcome ??
              (items.length
                ? result.truncated
                  ? "partial"
                  : "complete"
                : "empty"),
            count: items.length,
          });
          emit(true);
        } catch (error) {
          if (generation !== this.generation || controller.signal.aborted)
            return;
          statuses.push({
            providerId: provider.id,
            outcome: local.signal.aborted
              ? "timed_out"
              : (error as { status?: number }).status === 404
                ? "not_configured"
                : "unavailable",
            count: 0,
          });
          emit(true);
        } finally {
          clearTimeout(timer);
          controller.signal.removeEventListener("abort", abort);
        }
      }),
    );
    clearTimeout(deadline);
    emit(false);
  }
}
