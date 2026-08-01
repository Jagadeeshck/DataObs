import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  consoleRoutes,
  routeForPath,
  visibleRoutes,
  type NavigationGroup,
} from "../app/routes";
import { DataStatusBanner, LoadingSkeleton } from "../components/Evidence";
import { useProductContext } from "../state/context";
import { QuickFind } from "../features/quick-find/QuickFind";
import { useEffect } from "react";

export function ProductContextSelector() {
  const { tenant, environment, availableTenants, setTenant, setEnvironment } =
    useProductContext();
  const current = availableTenants.find((item) => item.id === tenant);
  return (
    <div className="context-selectors">
      <label>
        Tenant
        <select
          aria-label="Tenant"
          value={tenant}
          onChange={(event) => setTenant(event.target.value)}
        >
          {availableTenants.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name ?? item.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        Environment
        <select
          aria-label="Environment"
          value={environment}
          onChange={(event) => setEnvironment(event.target.value)}
        >
          {current?.environments.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
export function TimeRangeSelector() {
  const { timeRange, setTimeRange } = useProductContext();
  return (
    <label>
      Time range
      <select
        aria-label="Time range"
        value={timeRange}
        onChange={(event) =>
          setTimeRange(event.target.value as typeof timeRange)
        }
      >
        <option value="1h">Last hour</option>
        <option value="6h">Last 6 hours</option>
        <option value="24h">Last 24 hours</option>
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
      </select>
    </label>
  );
}
export function GlobalRefreshControl() {
  const { requestRefresh, autoRefreshSeconds, setAutoRefreshSeconds } =
    useProductContext();
  return (
    <div className="refresh-controls">
      <button onClick={requestRefresh} aria-label="Refresh all page evidence">
        ↻ Refresh
      </button>
      <label>
        <span className="sr-only">Auto refresh</span>
        <select
          aria-label="Auto refresh"
          value={autoRefreshSeconds ?? 0}
          onChange={(event) =>
            setAutoRefreshSeconds(Number(event.target.value) || null)
          }
        >
          <option value="0">Auto refresh off</option>
          <option value="30">Every 30s</option>
          <option value="60">Every minute</option>
        </select>
      </label>
    </div>
  );
}
export function UserMenu() {
  const { identity } = useProductContext();
  const name = identity?.displayName ?? identity?.email ?? "Signed-in user";
  const initials =
    identity?.displayName
      ?.split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() ?? "U";
  return (
    <details className="user-menu">
      <summary aria-label={`User menu for ${name}`}>
        <span className="avatar">{initials}</span>
        <span>{name}</span>
      </summary>
      <NavLink to="/logout">Sign out</NavLink>
    </details>
  );
}
export function AppHeader() {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-mark">D</span>
        <div>
          <strong>DataObs</strong>
          <small>CONSOLE</small>
        </div>
      </div>
      <div className="context">
        <QuickFind />
        <ProductContextSelector />
        <TimeRangeSelector />
        <GlobalRefreshControl />
      </div>
      <UserMenu />
    </header>
  );
}
export function PrimaryNavigation() {
  const { identity } = useProductContext();
  const groups: NavigationGroup[] = [
    "Overview",
    "Observe",
    "Respond",
    "Configure",
  ];
  const routes = visibleRoutes(identity?.permissions ?? []);
  return (
    <nav aria-label="Primary">
      {groups.map((group) => (
        <section key={group} aria-labelledby={`nav-${group}`}>
          <h2 id={`nav-${group}`}>{group}</h2>
          {routes
            .filter((route) => route.group === group && route.navigation)
            .map((route) =>
              route.availability === "available" ||
              route.availability === "preview" ? (
                <NavLink
                  key={route.id}
                  to={route.path}
                  end={route.path === "/"}
                >
                  {route.icon} <span>{route.name}</span>
                  {route.availability === "preview" && <em>Preview</em>}
                </NavLink>
              ) : (
                <span
                  className="nav-disabled"
                  key={route.id}
                  aria-disabled="true"
                >
                  {route.icon} <b>{route.name}</b>
                  <em>{route.availability.replace("_", " ")}</em>
                </span>
              ),
            )}
        </section>
      ))}
    </nav>
  );
}
export function Breadcrumbs() {
  const location = useLocation();
  const route = routeForPath(location.pathname);
  const parent = route?.parentId
    ? consoleRoutes.find((candidate) => candidate.id === route.parentId)
    : undefined;
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <NavLink to="/">DataObs</NavLink>
      {parent && (
        <>
          <span aria-hidden="true">/</span>
          <NavLink to={parent.path}>{parent.breadcrumb}</NavLink>
        </>
      )}
      {route?.id !== "command-center" && <span aria-hidden="true">/</span>}
      <span aria-current="page">{route?.breadcrumb ?? "Unknown route"}</span>
    </nav>
  );
}
export function ConnectivityBanner() {
  const { identity } = useProductContext();
  const gaps = consoleRoutes.filter(
    (route) => identity?.capabilities?.[route.id] === "unavailable",
  ).length;
  return gaps ? (
    <DataStatusBanner state="partial">
      {gaps} product {gaps === 1 ? "capability is" : "capabilities are"}{" "}
      currently unavailable.
    </DataStatusBanner>
  ) : null;
}
export function AppShell() {
  const { status, retryAuthentication } = useProductContext();
  const location = useLocation();
  useEffect(() => {
    document.title = `${routeForPath(location.pathname)?.name ?? "Page not found"} · DataObs`;
  }, [location.pathname]);
  if (status === "loading")
    return (
      <main className="route-state">
        <LoadingSkeleton label="Establishing secure Console context…" />
      </main>
    );
  if (status === "unauthorised")
    return (
      <main className="route-state">
        <h1>Access denied</h1>
        <p>
          Your authenticated identity has no trusted tenant and environment
          membership.
        </p>
        <NavLink to="/login">Sign in with another account</NavLink>
      </main>
    );
  if (status === "unavailable")
    return (
      <main className="route-state">
        <h1>Console unavailable</h1>
        <DataStatusBanner state="unavailable">
          The authenticated product context could not be loaded.{" "}
          <button onClick={retryAuthentication}>Retry</button>
        </DataStatusBanner>
      </main>
    );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <AppHeader />
      <aside>
        <PrimaryNavigation />
      </aside>
      <main id="main-content" tabIndex={-1}>
        <Breadcrumbs />
        <ConnectivityBanner />
        <Outlet />
      </main>
    </div>
  );
}
