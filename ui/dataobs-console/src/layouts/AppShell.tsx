import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  consoleRoutes,
  routeForPath,
  matchRoute,
  visibleRoutes,
  visibleWorkspaces,
  workspaceForId,
  breadcrumbsForPath,
  safeParentPath,
  type ConsoleWorkspace,
} from "../app/routes";
import { investigationPath } from "../investigation/context";
import { DataStatusBanner, LoadingSkeleton } from "../components/Evidence";
import { useProductContext } from "../state/context";
import { QuickFind } from "../features/quick-find/QuickFind";
import { useEffect, useRef, useState } from "react";

export function ProductContextSelector() {
  const { tenant, environment, availableTenants, setTenant, setEnvironment } =
    useProductContext();
  const current = availableTenants.find((item) => item.id === tenant);
  return (
    <details className="context-selector">
      <summary
        aria-label={`Current context: ${current?.name ?? tenant} / ${environment}`}
      >
        <small>Tenant / Environment</small>
        <strong>
          {current?.name ?? tenant} / {environment}
        </strong>
      </summary>
      <div className="context-selector-panel">
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
        <small>
          Changing context clears scoped evidence and returns detail pages to a
          safe parent.
        </small>
      </div>
    </details>
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
export function WorkspaceSwitcher() {
  const location = useLocation();
  const navigate = useNavigate();
  const { identity } = useProductContext();
  const current = routeForPath(location.pathname);
  const workspaces = visibleWorkspaces(identity?.permissions ?? []);
  return (
    <label className="workspace-switcher">
      <span className="sr-only">Workspace</span>
      <select
        aria-label="Workspace"
        value={current?.workspace ?? "home"}
        onChange={(event) =>
          navigate(
            workspaceForId(event.target.value as ConsoleWorkspace).defaultPath,
          )
        }
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.label}
          </option>
        ))}
      </select>
    </label>
  );
}
export function AppHeader({
  onOpenNavigation,
}: {
  onOpenNavigation: () => void;
}) {
  return (
    <header className="app-header">
      <button
        className="mobile-nav-trigger"
        onClick={onOpenNavigation}
        aria-label="Open product navigation"
      >
        ☰
      </button>
      <div className="brand">
        <span className="brand-mark">D</span>
        <div>
          <strong>DataObs</strong>
          <small>CONSOLE</small>
        </div>
      </div>
      <WorkspaceSwitcher />
      <div className="header-search">
        <QuickFind />
      </div>
      <div className="context">
        <NavLink
          className="activity-indicator"
          to="/activity"
          aria-label="Open Activity Center"
        >
          ◉ <span>Activity</span>
        </NavLink>
        <ProductContextSelector />
        <TimeRangeSelector />
        <GlobalRefreshControl />
      </div>
      <UserMenu />
    </header>
  );
}
export function PrimaryNavigation({
  collapsed,
  onToggle,
  onNavigate,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}) {
  const location = useLocation();
  const { identity } = useProductContext();
  const current = routeForPath(location.pathname);
  const permissions = identity?.permissions ?? [];
  const workspaces = visibleWorkspaces(permissions);
  const routes = visibleRoutes(permissions);
  const activeWorkspace = current?.workspace ?? "home";
  const capabilityRoutes = routes.filter(
    (route) =>
      route.workspace === activeWorkspace &&
      route.navigationLevel === "secondary",
  );
  const capability = current?.capabilityId;
  const contextualRoutes = routes.filter(
    (route) =>
      route.workspace === activeWorkspace &&
      route.navigationLevel === "contextual" &&
      route.capabilityId === capability,
  );
  return (
    <nav
      aria-label="Product navigation"
      className={collapsed ? "collapsed" : undefined}
    >
      <div className="workspace-navigation" aria-label="Workspaces">
        {workspaces.map((workspace) => (
          <NavLink
            key={workspace.id}
            to={workspace.defaultPath}
            onClick={onNavigate}
            aria-label={workspace.label}
            className={workspace.id === activeWorkspace ? "active" : undefined}
            title={collapsed ? workspace.label : undefined}
          >
            <span aria-hidden="true">{workspace.icon}</span>
            <span>{workspace.label}</span>
          </NavLink>
        ))}
      </div>
      {!collapsed && (
        <section aria-labelledby="capabilities-heading">
          <h2 id="capabilities-heading">
            {workspaceForId(activeWorkspace).label} capabilities
          </h2>
          {capabilityRoutes.map((route) => (
            <NavLink
              key={route.id}
              to={route.path}
              end={route.path === "/"}
              onClick={onNavigate}
            >
              {route.icon}
              <span>{route.name}</span>
              {route.availability === "preview" && <em>Preview</em>}
            </NavLink>
          ))}
        </section>
      )}
      {!collapsed && contextualRoutes.length > 0 && (
        <section
          className="contextual-navigation"
          aria-labelledby="contextual-heading"
        >
          <h2 id="contextual-heading">In this capability</h2>
          {contextualRoutes.map((route) => (
            <NavLink key={route.id} to={route.path} onClick={onNavigate}>
              {route.name}
            </NavLink>
          ))}
        </section>
      )}
      <button
        className="nav-collapse"
        onClick={onToggle}
        aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
        aria-expanded={!collapsed}
      >
        {collapsed ? "»" : "« Collapse"}
      </button>
    </nav>
  );
}
export function Breadcrumbs() {
  const location = useLocation();
  const crumbs = breadcrumbsForPath(location.pathname);
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <NavLink to="/">DataObs</NavLink>
      {crumbs.map((crumb, index) => (
        <span className="breadcrumb-item" key={crumb.id}>
          <span aria-hidden="true">/</span>
          {index === crumbs.length - 1 ? (
            <span aria-current="page">{crumb.label}</span>
          ) : (
            <NavLink to={crumb.path}>{crumb.label}</NavLink>
          )}
        </span>
      ))}
    </nav>
  );
}
export function ContextSwitchSafety() {
  const { contextSwitchGeneration } = useProductContext();
  const location = useLocation();
  const navigate = useNavigate();
  const previous = useRef(contextSwitchGeneration);
  useEffect(() => {
    if (previous.current === contextSwitchGeneration) return;
    previous.current = contextSwitchGeneration;
    const current = routeForPath(location.pathname);
    if (current?.entityParameters?.length) {
      navigate(safeParentPath(current), { replace: true });
    }
  }, [contextSwitchGeneration, location.pathname, navigate]);
  return null;
}
export function InvestigateCurrentEntity() {
  const location = useLocation();
  const route = routeForPath(location.pathname);
  const parameter = route?.entityParameters?.[0];
  const params = route ? matchRoute(route.path, location.pathname) : null;
  const entityId = parameter && params?.[parameter.name];
  if (
    !route ||
    !parameter ||
    !entityId ||
    route.id === "investigation-workspace"
  )
    return null;
  return (
    <div className="shell-investigate">
      <NavLink
        to={investigationPath(
          {
            entityType: parameter.entityType.replaceAll(
              "-",
              "_",
            ) as import("../app/entityLinks").EntityType,
            entityId,
            routeId: route.id,
            routeParameters: { [parameter.name]: entityId },
          },
          location.pathname,
        )}
      >
        Investigate
      </NavLink>
    </div>
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
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("dataobs:shell:collapsed") === "true",
  );
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
      <AppHeader onOpenNavigation={() => setNavigationOpen(true)} />
      {navigationOpen && (
        <button
          className="navigation-backdrop"
          aria-label="Close product navigation"
          onClick={() => setNavigationOpen(false)}
        />
      )}
      <aside
        className={`${collapsed ? "is-collapsed" : ""} ${navigationOpen ? "is-open" : ""}`}
      >
        <PrimaryNavigation
          collapsed={collapsed}
          onNavigate={() => setNavigationOpen(false)}
          onToggle={() =>
            setCollapsed((value) => {
              localStorage.setItem("dataobs:shell:collapsed", String(!value));
              return !value;
            })
          }
        />
      </aside>
      <main id="main-content" tabIndex={-1}>
        <ContextSwitchSafety />
        <Breadcrumbs />
        <InvestigateCurrentEntity />
        <ConnectivityBanner />
        <Outlet />
      </main>
    </div>
  );
}
