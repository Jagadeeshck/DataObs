import { request } from "../api/transport";
import type {
  ConfigurationView,
  DiagnosticsView,
  KnownIssuesView,
  MaintenanceView,
  ReadinessView,
  SupportabilitySection,
  SupportabilitySnapshot,
  SupportView,
} from "./supportabilityTypes";

const paths: Array<[SupportabilitySection, keyof SupportabilitySnapshot]> = [
  ["support", "support"],
  ["diagnostics", "diagnostics"],
  ["configuration", "configuration"],
  ["maintenance", "maintenance"],
  ["known-issues", "knownIssues"],
  ["operational-readiness", "readiness"],
];
type View =
  | SupportView
  | DiagnosticsView
  | ConfigurationView
  | MaintenanceView
  | KnownIssuesView
  | ReadinessView;
const inflight = new Map<string, Promise<View>>();

function section(
  section: SupportabilitySection,
  signal?: AbortSignal,
): Promise<View> {
  const existing = inflight.get(section);
  if (existing) return existing;
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort("section_timeout"),
    2000,
  );
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  const promise = request<View>(`/api/v1/platform/${section}`, undefined, {
    signal: controller.signal,
  })
    .then(({ data }) => data)
    .finally(() => {
      window.clearTimeout(timeout);
      signal?.removeEventListener("abort", abort);
      inflight.delete(section);
    });
  inflight.set(section, promise);
  return promise;
}

export const supportabilityClient = {
  snapshot: async (signal?: AbortSignal): Promise<SupportabilitySnapshot> => {
    const settled = await Promise.allSettled(
      paths.map(([name]) => section(name, signal)),
    );
    const snapshot: SupportabilitySnapshot = { failures: [] };
    settled.forEach((result, index) => {
      const [sectionName, property] = paths[index];
      if (result.status === "fulfilled")
        Object.assign(snapshot, { [property]: result.value });
      else snapshot.failures.push(sectionName);
    });
    return snapshot;
  },
};
