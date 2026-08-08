import { mergeActivity } from "./ranking";
import type {
  ActivityProvider,
  ActivityProviderResult,
  ActivityRequest,
} from "./types";
export const MAX_ACTIVITY_ITEMS = 150,
  GLOBAL_DEADLINE_MS = 4_000;
export interface ActivityLoad {
  items: ReturnType<typeof mergeActivity>;
  providers: Record<string, ActivityProviderResult["outcome"]>;
  permissionLimited: boolean;
}
export async function loadActivity(
  providers: readonly ActivityProvider[],
  request: ActivityRequest,
  signal?: AbortSignal,
): Promise<ActivityLoad> {
  const global = new AbortController();
  const abort = () => global.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  const deadline = window.setTimeout(
    () => global.abort("global_deadline"),
    GLOBAL_DEADLINE_MS,
  );
  const statuses: Record<string, ActivityProviderResult["outcome"]> = {};
  let permissionLimited = false;
  const eligible = providers.filter((provider) => {
    const permitted =
      !provider.requiredPermission ||
      request.context.permissions.includes(provider.requiredPermission);
    if (!permitted) permissionLimited = true;
    return permitted && provider.supports(request.context);
  });
  const results = await Promise.all(
    eligible.map(async (provider) => {
      const local = new AbortController();
      const onGlobalAbort = () => local.abort(global.signal.reason);
      global.signal.addEventListener("abort", onGlobalAbort, { once: true });
      const timeout = window.setTimeout(
        () => local.abort("provider_timeout"),
        provider.timeoutMs,
      );
      try {
        const result = await provider.load(
          {
            ...request,
            maximumItems: Math.min(request.maximumItems, provider.maximumItems),
          },
          local.signal,
        );
        statuses[provider.id] = result.outcome;
        return result.items;
      } catch (error) {
        statuses[provider.id] =
          local.signal.reason === "provider_timeout"
            ? "timed_out"
            : "unavailable";
        if (signal?.aborted) throw error;
        return [];
      } finally {
        clearTimeout(timeout);
        global.signal.removeEventListener("abort", onGlobalAbort);
      }
    }),
  );
  clearTimeout(deadline);
  signal?.removeEventListener("abort", abort);
  return {
    items: mergeActivity(results.flat(), MAX_ACTIVITY_ITEMS),
    providers: statuses,
    permissionLimited,
  };
}
