export type Health =
  | "healthy"
  | "warning"
  | "critical"
  | "unknown"
  | "not_configured"
  | "unavailable"
  | "stale"
  | "partial";
export interface DataStatus {
  complete: boolean;
  warnings: string[];
  sources: string[];
  observed_at?: string;
  missing_inputs?: string[];
  source_coverage?: number;
  confidence?: number;
}
export interface Pillar {
  id: string;
  name: string;
  health: Health;
  metric: string;
  issues?: number;
  coverage?: string;
  observed_at?: string;
  missing_evidence?: string[];
  trend?: string;
}
export interface PriorityItem {
  id: string;
  problem: string;
  entity: string;
  owner?: string;
  service?: string;
  started?: string;
  severity: string;
  impact?: string;
  automation?: string;
  href?: string;
  state?: string;
}
export interface CommandCenter {
  overall_health: Health;
  pillars: Pillar[];
  priority_items: PriorityItem[];
  recent_changes: { id: string; title: string; detail: string; time: string }[];
  critical_incidents?: number;
  affected_services?: number;
  data_status: DataStatus;
}
export interface TopologyNode {
  id: string;
  name: string;
  type: string;
  health: Health;
  owner?: string;
  business_service?: string;
  badges?: string[];
}
export interface TopologyEdge {
  id: string;
  source_node_id: string;
  destination_node_id: string;
  health?: Health;
  confidence?: number;
  evidence_state?:
    | "observed"
    | "derived"
    | "inferred"
    | "partial"
    | "unknown"
    | "stale";
  observed_at?: string;
  evidence_references?: string[];
  throughput?: number;
}
export interface Topology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  truncated: boolean;
  data_status: DataStatus;
}
