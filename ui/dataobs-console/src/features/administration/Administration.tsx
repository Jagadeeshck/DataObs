import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/common";
import {
  administrationApi,
  canonicalRoles,
  type CanonicalRole,
  type PrincipalType,
  type RoleBinding,
} from "../../api/administration";
import { useProductContext } from "../../state/context";
import { presentPermission } from "./catalogue";

export function AdminPageHeader({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="admin-page-header">
      <div>
        <p className="eyebrow">Administration</p>
        <h1>{title}</h1>
      </div>
      {children}
    </header>
  );
}
export function SafeIdentifier({ value }: { value: string }) {
  return <code className="safe-identifier">{value}</code>;
}
export function PermissionBadge({ permission }: { permission: string }) {
  const item = presentPermission(permission);
  return (
    <span className={`admin-badge risk-${item.risk}`} title={item.description}>
      {item.label}
    </span>
  );
}
export function LastAdministratorNotice() {
  return (
    <div className="admin-notice danger" role="alert">
      <strong>Safety control applied.</strong>
      <p>
        This binding cannot be removed because it would remove the last
        administrator for this scope.
      </p>
    </div>
  );
}
const scopeOf = (tenant: string, environment: string) => ({
  tenant,
  environment,
});

export function AdministrationOverview() {
  const { identity, tenant, environment } = useProductContext();
  return (
    <section className="admin-page">
      <AdminPageHeader title="Administration" />
      <p className="admin-lede">
        Understand trusted access and operate supported access-management
        contracts without weakening server enforcement.
      </p>
      <div className="admin-grid">
        <article>
          <h2>Current principal</h2>
          <dl>
            <dt>Display name</dt>
            <dd>{identity?.displayName ?? "Unknown"}</dd>
            <dt>Principal type</dt>
            <dd>{identity?.principalType ?? "Unknown"}</dd>
            <dt>Subject</dt>
            <dd>
              <SafeIdentifier value={identity?.subject ?? "Unavailable"} />
            </dd>
          </dl>
          <Link to="/administration/my-access">Review my access</Link>
        </article>
        <article>
          <h2>Trusted scope</h2>
          <dl>
            <dt>Tenant</dt>
            <dd>{tenant || "Unavailable"}</dd>
            <dt>Environment</dt>
            <dd>{environment || "Unavailable"}</dd>
            <dt>Memberships</dt>
            <dd>{identity?.tenants.length ?? 0} available</dd>
          </dl>
        </article>
        <article>
          <h2>Access management</h2>
          <p>
            Durable role-binding operations are protected by backend IAM
            permissions, ETags and safety controls.
          </p>
          <Link to="/administration/access">Open role bindings</Link>
        </article>
        <article>
          <h2>Security audit</h2>
          <p>
            <strong>Unavailable.</strong> No bounded audit-event read API is
            currently exposed.
          </p>
          <Link to="/administration/audit">Review limitation</Link>
        </article>
      </div>
    </section>
  );
}

export function MyAccess() {
  const { identity, tenant, environment } = useProductContext();
  const grouped = useMemo(
    () =>
      Object.entries(
        (identity?.permissions ?? []).reduce<Record<string, string[]>>(
          (groups, permission) => {
            const group = presentPermission(permission).group;
            (groups[group] ??= []).push(permission);
            return groups;
          },
          {},
        ),
      ),
    [identity?.permissions],
  );
  return (
    <section className="admin-page">
      <AdminPageHeader title="My access" />
      <div className="admin-grid">
        <article>
          <h2>Trusted identity</h2>
          <dl>
            <dt>Display name</dt>
            <dd>{identity?.displayName ?? "Not supplied"}</dd>
            <dt>Safe subject</dt>
            <dd>
              <SafeIdentifier value={identity?.subject ?? "Unavailable"} />
            </dd>
            <dt>Principal type</dt>
            <dd>{identity?.principalType ?? "Unknown"}</dd>
            <dt>Provider</dt>
            <dd>{identity?.authenticationProvider ?? "Not supplied"}</dd>
            <dt>Session expiry</dt>
            <dd>{identity?.tokenExpiry ?? "Not supplied"}</dd>
          </dl>
        </article>
        <article>
          <h2>Active scope</h2>
          <dl>
            <dt>Tenant</dt>
            <dd>{tenant}</dd>
            <dt>Environment</dt>
            <dd>{environment}</dd>
            <dt>Access source</dt>
            <dd>Backend-resolved trusted principal</dd>
          </dl>
        </article>
      </div>
      <h2>Effective roles</h2>
      <div className="badge-list">
        {identity?.roles?.map((r) => (
          <span className="admin-badge" key={r}>
            {r}
          </span>
        )) || "Not supplied"}
      </div>
      <h2>Effective permissions</h2>
      {grouped.map(([group, permissions]) => (
        <section key={group}>
          <h3>{group}</h3>
          <div className="badge-list">
            {permissions?.map((p) => (
              <PermissionBadge key={p} permission={p} />
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}

function useBindings() {
  const { tenant, environment, refreshGeneration } = useProductContext();
  const [state, setState] = useState<{
    items?: RoleBinding[];
    error?: ApiError;
  }>({});
  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- context changes invalidate prior tenant evidence
    setState({});
    administrationApi
      .list(scopeOf(tenant, environment), controller.signal)
      .then((r) => setState({ items: r.data.items }))
      .catch((e) => {
        if (!controller.signal.aborted) setState({ error: e as ApiError });
      });
    return () => controller.abort();
  }, [tenant, environment, refreshGeneration]);
  return state;
}
export function AccessInventory() {
  const { items, error } = useBindings();
  const [role, setRole] = useState("");
  const visible = role
    ? items?.filter((b) => b.roles.includes(role as CanonicalRole))
    : items;
  return (
    <section className="admin-page">
      <AdminPageHeader title="Role bindings">
        <Link className="primary-action" to="/administration/access/new">
          Create binding
        </Link>
      </AdminPageHeader>
      <div className="admin-notice">
        <strong>Trusted scope only.</strong> Results are supplied by the backend
        for the active tenant; the current API has no server filtering or
        pagination contract.
      </div>
      <label className="admin-filter">
        Role{" "}
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">All measured results</option>
          {canonicalRoles.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      {error ? (
        <p role="alert">
          Role bindings are unavailable. Request ID:{" "}
          {error.requestId ?? "not supplied"}
        </p>
      ) : !items ? (
        <p role="status">Loading role bindings…</p>
      ) : visible?.length === 0 ? (
        <p>No role bindings were returned for this trusted scope.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Principal</th>
                <th>Type</th>
                <th>Roles</th>
                <th>Environments</th>
                <th>Status</th>
                <th>Revision</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {visible?.map((b) => (
                <tr key={b.binding_id}>
                  <td>
                    <SafeIdentifier value={b.principal_id} />
                  </td>
                  <td>{b.principal_type}</td>
                  <td>{b.roles.join(", ")}</td>
                  <td>{b.environments.join(", ")}</td>
                  <td>{b.active ? "Active" : "Disabled"}</td>
                  <td>{b.revision}</td>
                  <td>
                    <Link
                      to={`/administration/access/${encodeURIComponent(b.binding_id)}`}
                    >
                      View binding
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function CreateBinding() {
  const { tenant, environment } = useProductContext();
  const navigate = useNavigate();
  const [principalType, setPrincipalType] = useState<PrincipalType>("user"),
    [subject, setSubject] = useState(""),
    [role, setRole] = useState<CanonicalRole | "">(""),
    [review, setReview] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<ApiError>();
  const submit = async () => {
    if (!role || busy) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await administrationApi.create(
        scopeOf(tenant, environment),
        {
          issuer: "oidc",
          principal_type: principalType,
          principal_id: subject.trim(),
          tenant_id: tenant,
          environments: [environment],
          roles: [role],
          description: "",
        },
        crypto.randomUUID(),
      );
      navigate(
        `/administration/access/${encodeURIComponent(result.data.binding_id)}`,
      );
    } catch (e) {
      setError(e as ApiError);
      setBusy(false);
    }
  };
  return (
    <section className="admin-page">
      <AdminPageHeader title="Create role binding" />
      {!review ? (
        <form
          className="admin-form"
          onSubmit={(e) => {
            e.preventDefault();
            setReview(true);
          }}
        >
          <label>
            Principal type
            <select
              value={principalType}
              onChange={(e) =>
                setPrincipalType(e.target.value as PrincipalType)
              }
            >
              <option value="user">User</option>
              <option value="group">Group</option>
              <option value="service">Service principal</option>
            </select>
          </label>
          <label>
            Subject identifier
            <input
              required
              minLength={1}
              maxLength={256}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </label>
          <label>
            Canonical role
            <select
              required
              value={role}
              onChange={(e) => setRole(e.target.value as CanonicalRole)}
            >
              <option value="">Choose a role—no privileged default</option>
              {canonicalRoles.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <p>
            Scope:{" "}
            <strong>
              {tenant} / {environment}
            </strong>
          </p>
          <button className="primary-action">Review binding</button>
        </form>
      ) : (
        <div className="mutation-review">
          <h2>Review access grant</h2>
          <dl>
            <dt>Principal</dt>
            <dd>
              <SafeIdentifier value={subject} />
            </dd>
            <dt>Type</dt>
            <dd>{principalType}</dd>
            <dt>Role</dt>
            <dd>{role}</dd>
            <dt>Tenant / environment</dt>
            <dd>
              {tenant} / {environment}
            </dd>
          </dl>
          <p>
            This operation grants the permissions in the canonical backend role.
          </p>
          {error && (
            <p role="alert">
              Creation was rejected. Request ID:{" "}
              {error.requestId ?? "not supplied"}
            </p>
          )}
          <button onClick={() => setReview(false)} disabled={busy}>
            Back
          </button>{" "}
          <button className="primary-action" onClick={submit} disabled={busy}>
            {busy ? "Creating…" : "Confirm and create"}
          </button>
        </div>
      )}
    </section>
  );
}

export function BindingDetail() {
  const { bindingId = "" } = useParams();
  const { tenant, environment, identity } = useProductContext();
  const canWrite = identity?.permissions.includes("iam:write") ?? false;
  const [binding, setBinding] = useState<RoleBinding>();
  const [error, setError] = useState<ApiError>();
  const [confirm, setConfirm] = useState(false);
  const [lastAdmin, setLastAdmin] = useState(false);
  const load = () =>
    administrationApi
      .get(scopeOf(tenant, environment), bindingId)
      .then((r) => {
        setBinding(r.data);
        setError(undefined);
      })
      .catch((e) => setError(e as ApiError));
  useEffect(() => {
    void load();
    // Binding identity and trusted scope changes require a fresh, non-merged representation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bindingId, tenant, environment]);
  const revoke = async () => {
    if (!binding) return;
    try {
      await administrationApi.revoke(
        scopeOf(tenant, environment),
        binding.binding_id,
        binding.etag,
        crypto.randomUUID(),
      );
      setBinding({ ...binding, active: false });
      setConfirm(false);
    } catch (e) {
      const err = e as ApiError;
      setError(err);
      if (err.status === 409 && binding.roles.includes("platform_admin"))
        setLastAdmin(true);
    }
  };
  if (error?.status === 404)
    return (
      <section className="admin-page">
        <h1>Role binding not found</h1>
        <p>It may have been removed or is outside the trusted scope.</p>
      </section>
    );
  return (
    <section className="admin-page">
      <AdminPageHeader title="Role binding detail">
        <Link to="/administration/access">Return to inventory</Link>
      </AdminPageHeader>
      {error && (
        <p role="alert">
          The operation stopped safely. Request ID:{" "}
          {error.requestId ?? "not supplied"}
        </p>
      )}
      {lastAdmin && <LastAdministratorNotice />}
      {!binding ? (
        <p role="status">Loading role binding…</p>
      ) : (
        <>
          <dl className="admin-facts">
            <dt>Binding identifier</dt>
            <dd>
              <SafeIdentifier value={binding.binding_id} />
            </dd>
            <dt>Subject</dt>
            <dd>
              <SafeIdentifier value={binding.principal_id} />
            </dd>
            <dt>Principal type</dt>
            <dd>{binding.principal_type}</dd>
            <dt>Roles</dt>
            <dd>{binding.roles.join(", ")}</dd>
            <dt>Scope</dt>
            <dd>
              {binding.tenant_id} / {binding.environments.join(", ")}
            </dd>
            <dt>State</dt>
            <dd>{binding.active ? "Active" : "Disabled"}</dd>
            <dt>Created</dt>
            <dd>
              {binding.created_at} by {binding.created_by}
            </dd>
            <dt>Updated</dt>
            <dd>
              {binding.updated_at} by {binding.updated_by}
            </dd>
            <dt>Revision</dt>
            <dd>{binding.revision}</dd>
          </dl>
          {canWrite && binding.active && !confirm && (
            <button className="danger-action" onClick={() => setConfirm(true)}>
              Revoke access…
            </button>
          )}
          {confirm && (
            <div
              className="mutation-review"
              role="dialog"
              aria-modal="true"
              aria-labelledby="revoke-title"
            >
              <h2 id="revoke-title">Review revocation</h2>
              <p>
                Revoking this binding disables access for{" "}
                <SafeIdentifier value={binding.principal_id} /> in{" "}
                {binding.tenant_id} / {binding.environments.join(", ")} after
                backend confirmation.
              </p>
              <button onClick={() => setConfirm(false)}>Cancel</button>{" "}
              <button className="danger-action" onClick={revoke}>
                Confirm revoke
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
export function AccessAudit() {
  return (
    <section className="admin-page">
      <AdminPageHeader title="Access audit" />
      <div className="admin-notice">
        <strong>Unavailable.</strong>
        <p>
          The backend emits durable security events but exposes no bounded,
          redaction-safe read API. The Console does not query Elasticsearch
          directly.
        </p>
      </div>
    </section>
  );
}
export function SystemInformation() {
  return (
    <section className="admin-page">
      <AdminPageHeader title="System information" />
      <div className="admin-grid">
        <article>
          <h2>Console</h2>
          <p>Status: Running</p>
          <p>Version: 0.1.0</p>
        </article>
        <article>
          <h2>Certification</h2>
          <p>Status: Unknown</p>
          <p>Runtime health is not certification evidence.</p>
        </article>
        <article>
          <h2>Diagnostics</h2>
          <Link to="/diagnostics/console">
            Open privacy-safe Console diagnostics
          </Link>
        </article>
      </div>
    </section>
  );
}
const preferenceKey = "dataobs.console.preferences.v1";
export function Preferences() {
  const defaults = {
    density: "comfortable",
    timezone: "local",
    motion: "system",
  };
  const read = () => {
    try {
      const v = JSON.parse(localStorage.getItem(preferenceKey) ?? "{}");
      return {
        density: ["comfortable", "compact"].includes(v.density)
          ? v.density
          : defaults.density,
        timezone: ["local", "utc"].includes(v.timezone)
          ? v.timezone
          : defaults.timezone,
        motion: ["system", "reduced"].includes(v.motion)
          ? v.motion
          : defaults.motion,
      };
    } catch {
      return defaults;
    }
  };
  const [value, setValue] = useState(read);
  useEffect(
    () => localStorage.setItem(preferenceKey, JSON.stringify(value)),
    [value],
  );
  return (
    <section className="admin-page">
      <AdminPageHeader title="Console preferences" />
      <p>
        Only versioned, non-sensitive presentation choices are stored in this
        browser.
      </p>
      <form className="admin-form">
        <label>
          Table density
          <select
            value={value.density}
            onChange={(e) => setValue({ ...value, density: e.target.value })}
          >
            <option value="comfortable">Comfortable</option>
            <option value="compact">Compact</option>
          </select>
        </label>
        <label>
          Time zone display
          <select
            value={value.timezone}
            onChange={(e) => setValue({ ...value, timezone: e.target.value })}
          >
            <option value="local">Local</option>
            <option value="utc">UTC</option>
          </select>
        </label>
        <label>
          Animation
          <select
            value={value.motion}
            onChange={(e) => setValue({ ...value, motion: e.target.value })}
          >
            <option value="system">Follow system</option>
            <option value="reduced">Reduced</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            localStorage.removeItem(preferenceKey);
            setValue(defaults);
          }}
        >
          Reset to defaults
        </button>
      </form>
    </section>
  );
}
