export type ResourceKind =
  | "environment"
  | "installation"
  | "cluster"
  | "tenant";
export interface LifecycleResource {
  id: string;
  name?: string;
  state: string;
  revision: number;
  updated_at?: string;
  environment_id?: string;
  requested_environment?: string;
  installation_id?: string | null;
  cluster_id?: string | null;
  environment_class?: string;
  release_version?: string;
  candidate_version?: string;
  kubernetes_version?: string;
  desired_state_hash?: string;
  observed_state_hash?: string;
  drift_state?: string;
  drift?: string;
  health?: string;
  capacity_profile?: string;
  capacity_class?: string;
  tenant_count?: number;
  [key: string]: unknown;
}
export interface FleetResponse {
  items?: LifecycleResource[];
  environments?: number;
  clusters?: number;
  installations?: number;
  tenants?: number;
  [key: string]: unknown;
}
export interface DriftEvidence {
  resource_type?: string;
  resource_id?: string;
  environment_id?: string;
  desired_state_hash?: string;
  observed_state_hash?: string;
  drift_state?: string;
  detected_at?: string;
  evidence_state?: string;
  [key: string]: unknown;
}
export interface CapacityEvidence {
  state: string;
  profiles_reference?: string;
}
export interface OffboardingPreview {
  tenant_id?: string;
  revision?: number;
  resources?: unknown[];
  affected_resources?: unknown[];
  backup_verified?: boolean;
  backup_required?: boolean;
  approval_required?: boolean;
  blockers?: string[];
  warnings?: string[];
  [key: string]: unknown;
}
export type ProviderKey =
  | "fleet"
  | "environments"
  | "installations"
  | "clusters"
  | "tenants"
  | "drift"
  | "capacity";
export interface PlatformSnapshot {
  fleet?: FleetResponse;
  environments?: LifecycleResource[];
  installations?: LifecycleResource[];
  clusters?: LifecycleResource[];
  tenants?: LifecycleResource[];
  drift?: DriftEvidence[];
  capacity?: CapacityEvidence;
  failures: ProviderKey[];
}
