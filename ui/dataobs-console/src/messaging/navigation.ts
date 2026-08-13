import type { MessagingResourceKind } from "./types";
export function messagingResourceRoute(
  kind: MessagingResourceKind,
  canonicalId: string,
): string | null {
  const legacy: Partial<Record<MessagingResourceKind, string>> = {
    topic: "topics",
    consumer_group: "consumer-groups",
    connector: "connectors",
  };
  const root = legacy[kind];
  return root ? `/streams/${root}/${encodeURIComponent(canonicalId)}` : null;
}
