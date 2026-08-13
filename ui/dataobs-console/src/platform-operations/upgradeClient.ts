import { request } from "../api/transport";
import type {
  CompatibilityResponse,
  UpgradeReadinessResponse,
  UpgradeSnapshot,
} from "./upgradeTypes";

const inflight = new Map<string, Promise<unknown>>();
function bounded<T>(path: string, signal?: AbortSignal): Promise<T> {
  const existing = inflight.get(path) as Promise<T> | undefined;
  if (existing) return existing;
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort("upgrade_assessment_timeout"),
    4000,
  );
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  const value = request<T>(path, undefined, { signal: controller.signal })
    .then(({ data }) => data)
    .finally(() => {
      window.clearTimeout(timeout);
      signal?.removeEventListener("abort", abort);
      inflight.delete(path);
    });
  inflight.set(path, value);
  return value;
}
export const upgradeClient = {
  snapshot: async (
    target: string,
    signal?: AbortSignal,
  ): Promise<UpgradeSnapshot> => {
    const calls = await Promise.allSettled([
      bounded<CompatibilityResponse>("/api/v1/platform/compatibility", signal),
      bounded<UpgradeReadinessResponse>(
        `/api/v1/platform/upgrade-readiness?target=${encodeURIComponent(target)}`,
        signal,
      ),
    ]);
    const snapshot: UpgradeSnapshot = { failures: [] };
    if (calls[0].status === "fulfilled")
      snapshot.compatibility = calls[0].value;
    else snapshot.failures.push("compatibility");
    if (calls[1].status === "fulfilled") snapshot.readiness = calls[1].value;
    else snapshot.failures.push("upgrade-readiness");
    return snapshot;
  },
};
