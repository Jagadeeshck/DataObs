import { request } from "../api/transport";
import type {
  CapacityEvidence,
  DriftEvidence,
  FleetResponse,
  LifecycleResource,
  OffboardingPreview,
  PlatformSnapshot,
  ProviderKey,
} from "./types";

const inflight = new Map<string, Promise<unknown>>();
function bounded<T>(path: string, signal?: AbortSignal): Promise<T> {
  const existing = inflight.get(path) as Promise<T> | undefined;
  if (existing) return existing;
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort("provider_timeout"),
    2000,
  );
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  const promise = request<T>(path, undefined, { signal: controller.signal })
    .then((r) => r.data)
    .finally(() => {
      window.clearTimeout(timeout);
      signal?.removeEventListener("abort", abort);
      inflight.delete(path);
    });
  inflight.set(path, promise);
  return promise;
}
const list = (kind: string, signal?: AbortSignal) =>
  bounded<{ items: LifecycleResource[] }>(
    `/api/v1/platform/${kind}`,
    signal,
  ).then((x) => x.items);
export const platformClient = {
  snapshot: async (signal?: AbortSignal): Promise<PlatformSnapshot> => {
    const providers: [ProviderKey, Promise<unknown>][] = [
      ["fleet", bounded<FleetResponse>("/api/v1/platform/fleet", signal)],
      ["environments", list("environments", signal)],
      ["installations", list("installations", signal)],
      ["clusters", list("clusters", signal)],
      ["tenants", list("tenants", signal)],
      [
        "drift",
        bounded<{ items: DriftEvidence[] }>(
          "/api/v1/platform/drift",
          signal,
        ).then((x) => x.items),
      ],
      [
        "capacity",
        bounded<CapacityEvidence>("/api/v1/platform/capacity", signal),
      ],
    ];
    const settled = await Promise.allSettled(
      providers.map(([, value]) => value),
    );
    const snapshot: PlatformSnapshot = { failures: [] };
    settled.forEach((result, index) => {
      const key = providers[index][0];
      if (result.status === "fulfilled")
        Object.assign(snapshot, { [key]: result.value });
      else snapshot.failures.push(key);
    });
    return snapshot;
  },
  resource: (kind: string, id: string, signal?: AbortSignal) =>
    bounded<LifecycleResource>(
      `/api/v1/platform/${kind}s/${encodeURIComponent(id)}`,
      signal,
    ),
  offboardingPreview: (id: string, signal?: AbortSignal) =>
    bounded<OffboardingPreview>(
      `/api/v1/platform/tenants/${encodeURIComponent(id)}/offboarding-preview`,
      signal,
    ),
};
