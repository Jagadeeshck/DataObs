import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { accessToken } from "../auth/oidc";

export const timeRanges = ["1h", "6h", "24h", "7d", "30d"] as const;
export type TimeRange = (typeof timeRanges)[number];
export type AuthenticatedContext = {
  subject: string;
  displayName?: string;
  email?: string;
  principalType?: "user" | "group" | "service";
  roles?: string[];
  authenticationProvider?: string;
  tokenExpiry?: string;
  tenants: Array<{ id: string; name?: string; environments: string[] }>;
  permissions: string[];
  capabilities?: Record<
    string,
    "available" | "preview" | "not_configured" | "unavailable"
  >;
};
type ContextValue = {
  status: "loading" | "ready" | "unauthorised" | "unavailable";
  identity?: AuthenticatedContext;
  tenant: string;
  environment: string;
  availableTenants: AuthenticatedContext["tenants"];
  timeRange: TimeRange;
  refreshGeneration: number;
  autoRefreshSeconds: number | null;
  setTenant: (v: string) => void;
  setEnvironment: (v: string) => void;
  setTimeRange: (v: TimeRange) => void;
  requestRefresh: () => void;
  setAutoRefreshSeconds: (v: number | null) => void;
  retryAuthentication: () => void;
};

export function parseTimeRange(value: string | null): TimeRange {
  return timeRanges.includes(value as TimeRange) ? (value as TimeRange) : "24h";
}
export function timeRangeBounds(range: TimeRange, now = new Date()) {
  const amount = Number.parseInt(range, 10);
  const multiplier = range.endsWith("h") ? 3_600_000 : 86_400_000;
  return {
    start: new Date(now.getTime() - amount * multiplier).toISOString(),
    end: now.toISOString(),
  };
}
const ProductContext = createContext<ContextValue | null>(null);

async function authenticatedContext(
  signal: AbortSignal,
): Promise<AuthenticatedContext> {
  const token = await accessToken();
  const response = await fetch("/api/v1/auth/me", {
    signal,
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (response.status === 401 || response.status === 403)
    throw Object.assign(new Error("unauthorised"), { status: response.status });
  if (!response.ok) throw new Error("Authentication context unavailable");
  const body = (await response.json()) as Record<string, unknown>;
  const rawTenants = Array.isArray(body.tenants)
    ? body.tenants
    : body.tenant
      ? [{ id: body.tenant, environments: body.environments }]
      : [];
  return {
    subject: String(body.subject ?? body.sub ?? "authenticated-user"),
    displayName:
      typeof body.display_name === "string" ? body.display_name : undefined,
    email: typeof body.email === "string" ? body.email : undefined,
    principalType:
      body.principal_type === "group" || body.principal_type === "service"
        ? body.principal_type
        : "user",
    roles: Array.isArray(body.roles) ? body.roles.map(String) : [],
    authenticationProvider:
      typeof body.authentication_provider === "string"
        ? body.authentication_provider
        : undefined,
    tokenExpiry:
      typeof body.token_expiry === "string" ? body.token_expiry : undefined,
    permissions: Array.isArray(body.permissions)
      ? body.permissions.map(String)
      : [],
    tenants: rawTenants
      .map((entry) => {
        const item = entry as Record<string, unknown>;
        return {
          id: String(item.id),
          name: typeof item.name === "string" ? item.name : undefined,
          environments: Array.isArray(item.environments)
            ? item.environments.map(String)
            : [],
        };
      })
      .filter((entry) => entry.id && entry.environments.length),
    capabilities:
      typeof body.capabilities === "object"
        ? (body.capabilities as AuthenticatedContext["capabilities"])
        : undefined,
  };
}

export function ProductContextProvider({
  children,
  initialContext,
}: {
  children: ReactNode;
  initialContext?: AuthenticatedContext;
}) {
  const [identity, setIdentity] = useState<AuthenticatedContext | undefined>(
    initialContext,
  );
  const [status, setStatus] = useState<ContextValue["status"]>(
    initialContext ? "ready" : "loading",
  );
  const [attempt, setAttempt] = useState(0);
  const requestedTenant = new URLSearchParams(location.search).get("tenant");
  const requestedEnvironment = new URLSearchParams(location.search).get(
    "environment",
  );
  const [tenant, setTenantState] = useState("");
  const [environment, setEnvironmentState] = useState("");
  const [timeRange, setTimeRangeState] = useState(() =>
    parseTimeRange(new URLSearchParams(location.search).get("range")),
  );
  const [refreshGeneration, setRefreshGeneration] = useState(0);
  const [autoRefreshSeconds, setAutoRefreshSeconds] = useState<number | null>(
    null,
  );
  useEffect(() => {
    if (initialContext) return;
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- a retry explicitly starts authentication
    setStatus("loading");
    void authenticatedContext(controller.signal)
      .then((value) => {
        setIdentity(value);
        setStatus(value.tenants.length ? "ready" : "unauthorised");
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setStatus(
            (error as { status?: number }).status
              ? "unauthorised"
              : "unavailable",
          );
      });
    return () => controller.abort();
  }, [attempt, initialContext]);
  useEffect(() => {
    if (!identity?.tenants.length) return;
    const selectedTenant =
      identity.tenants.find((item) => item.id === requestedTenant) ??
      identity.tenants[0];
    const selectedEnvironment = selectedTenant.environments.includes(
      requestedEnvironment ?? "",
    )
      ? requestedEnvironment!
      : selectedTenant.environments[0];
    // eslint-disable-next-line react-hooks/set-state-in-effect -- trusted identity changes invalidate the selected context
    setTenantState(selectedTenant.id);
    setEnvironmentState(selectedEnvironment);
    setRefreshGeneration((value) => value + 1);
  }, [identity, requestedEnvironment, requestedTenant]);
  const updateUrl = useCallback((values: Record<string, string>) => {
    const query = new URLSearchParams(location.search);
    Object.entries(values).forEach(([key, value]) => query.set(key, value));
    history.replaceState({}, "", `${location.pathname}?${query.toString()}`);
  }, []);
  const setTenant = useCallback(
    (next: string) => {
      const trusted = identity?.tenants.find((item) => item.id === next);
      if (!trusted) return;
      const nextEnvironment = trusted.environments[0];
      setTenantState(next);
      setEnvironmentState(nextEnvironment);
      updateUrl({ tenant: next, environment: nextEnvironment });
      setRefreshGeneration((value) => value + 1);
    },
    [identity, updateUrl],
  );
  const setEnvironment = useCallback(
    (next: string) => {
      const trusted = identity?.tenants.find((item) => item.id === tenant);
      if (!trusted?.environments.includes(next)) return;
      setEnvironmentState(next);
      updateUrl({ environment: next });
      setRefreshGeneration((value) => value + 1);
    },
    [identity, tenant, updateUrl],
  );
  const setTimeRange = useCallback(
    (next: TimeRange) => {
      setTimeRangeState(next);
      updateUrl({ range: next });
      setRefreshGeneration((value) => value + 1);
    },
    [updateUrl],
  );
  useEffect(() => {
    if (!autoRefreshSeconds) return;
    let id: number | undefined;
    const schedule = () => {
      if (id !== undefined) clearInterval(id);
      id = undefined;
      if (document.visibilityState === "visible") {
        id = window.setInterval(
          () => setRefreshGeneration((value) => value + 1),
          autoRefreshSeconds * 1000,
        );
      }
    };
    schedule();
    document.addEventListener("visibilitychange", schedule);
    return () => {
      if (id !== undefined) clearInterval(id);
      document.removeEventListener("visibilitychange", schedule);
    };
  }, [autoRefreshSeconds]);
  const value = useMemo<ContextValue>(
    () => ({
      status,
      identity,
      tenant,
      environment,
      availableTenants: identity?.tenants ?? [],
      timeRange,
      refreshGeneration,
      autoRefreshSeconds,
      setTenant,
      setEnvironment,
      setTimeRange,
      requestRefresh: () => setRefreshGeneration((value) => value + 1),
      setAutoRefreshSeconds,
      retryAuthentication: () => setAttempt((value) => value + 1),
    }),
    [
      status,
      identity,
      tenant,
      environment,
      timeRange,
      refreshGeneration,
      autoRefreshSeconds,
      setTenant,
      setEnvironment,
      setTimeRange,
    ],
  );
  return (
    <ProductContext.Provider value={value}>{children}</ProductContext.Provider>
  );
}
export function useProductContext() {
  const value = useContext(ProductContext);
  if (!value) throw new Error("Product context unavailable");
  return value;
}
