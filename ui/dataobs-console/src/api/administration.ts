import { request, type TransportResult } from "./transport";

import {
  canonicalRoles,
  type CanonicalRole,
} from "../features/administration/canonical";
export { canonicalRoles, type CanonicalRole };
export type PrincipalType = "user" | "group" | "service";
export type RoleBinding = {
  binding_id: string;
  issuer: string;
  principal_type: PrincipalType;
  principal_id: string;
  tenant_id: string;
  environments: string[];
  roles: CanonicalRole[];
  active: boolean;
  description: string;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  revision: number;
  etag: string;
};
export type RoleBindingInput = Pick<
  RoleBinding,
  | "issuer"
  | "principal_type"
  | "principal_id"
  | "tenant_id"
  | "environments"
  | "roles"
  | "description"
>;
export type RoleBindingPatch = Partial<
  Pick<RoleBinding, "environments" | "roles" | "active" | "description">
>;
export type BindingList = { items: RoleBinding[]; next_cursor?: string };
type Scope = { tenant: string; environment: string };
const safeId = (value: string) => encodeURIComponent(value);

export const administrationApi = {
  list: (scope: Scope, signal?: AbortSignal) =>
    request<BindingList>("/api/v1/iam/role-bindings", scope.tenant, {
      signal,
      environment: scope.environment,
    }),
  get: (scope: Scope, id: string, signal?: AbortSignal) =>
    request<RoleBinding>(
      `/api/v1/iam/role-bindings/${safeId(id)}`,
      scope.tenant,
      { signal, environment: scope.environment },
    ),
  create: (
    scope: Scope,
    input: RoleBindingInput,
    idempotencyKey: string,
    signal?: AbortSignal,
  ) =>
    request<RoleBinding>("/api/v1/iam/role-bindings", scope.tenant, {
      method: "POST",
      body: input,
      signal,
      environment: scope.environment,
      idempotencyKey,
    }),
  update: (
    scope: Scope,
    id: string,
    patch: RoleBindingPatch,
    etag: string,
    idempotencyKey: string,
    signal?: AbortSignal,
  ) =>
    request<RoleBinding>(
      `/api/v1/iam/role-bindings/${safeId(id)}`,
      scope.tenant,
      {
        method: "PATCH",
        body: patch,
        signal,
        environment: scope.environment,
        ifMatch: etag,
        idempotencyKey,
      },
    ),
  revoke: (
    scope: Scope,
    id: string,
    etag: string,
    idempotencyKey: string,
    signal?: AbortSignal,
  ): Promise<TransportResult<void>> =>
    request<void>(`/api/v1/iam/role-bindings/${safeId(id)}`, scope.tenant, {
      method: "DELETE",
      signal,
      environment: scope.environment,
      ifMatch: etag,
      idempotencyKey,
    }),
};
