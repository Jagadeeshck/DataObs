export type EntityType =
  | "incident"
  | "monitor"
  | "job"
  | "run"
  | "pathway"
  | "kafka_cluster"
  | "topic"
  | "consumer_group"
  | "connector"
  | "schema_subject"
  | "data_product"
  | "asset"
  | "integration";
const templates: Record<EntityType, string> = {
  incident: "/incidents/:id",
  monitor: "/quality/monitors/:id",
  job: "/jobs/:id",
  run: "/runs/:id",
  pathway: "/pathways/:id",
  kafka_cluster: "/streams/clusters/:id",
  topic: "/streams/topics/:id",
  consumer_group: "/streams/consumer-groups/:id",
  connector: "/streams/connectors/:id",
  schema_subject: "/streams/schemas/:id",
  data_product: "/data-products/:id",
  asset: "/assets/:id",
  integration: "/integrations/:id",
};
export function entityLink(type: string, id: unknown): string | null {
  if (
    !(type in templates) ||
    typeof id !== "string" ||
    !id.trim() ||
    id.length > 512 ||
    [...id].some((character) => character.charCodeAt(0) < 32)
  )
    return null;
  return templates[type as EntityType].replace(":id", encodeURIComponent(id));
}
