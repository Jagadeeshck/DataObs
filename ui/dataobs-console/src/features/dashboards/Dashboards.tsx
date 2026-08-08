import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import type { CommandCenter } from "../../api/types";
import { buildRoutePath } from "../../app/routes";
import {
  DataStatusBanner,
  HealthBadge,
  LoadingSkeleton,
} from "../../components/Evidence";
import { timeRangeBounds, useProductContext } from "../../state/context";
import { adjustLayout, type LayoutAction } from "../../dashboards/layout";
import {
  requireWidget,
  widgetDetailsPath,
  widgetRegistrations,
} from "../../dashboards/registry";
import {
  cloneTemplate,
  loadSavedViews,
  resetSavedView,
  saveViews,
  upsertSavedView,
  type SafeSavedView,
} from "../../dashboards/savedViews";
import {
  dashboardTemplate,
  dashboardTemplates,
} from "../../dashboards/templates";
import type {
  DashboardDefinition,
  DashboardWidgetDefinition,
} from "../../dashboards/types";
import { contextFingerprint, WatchlistStore } from "../../dashboards/watchlist";

export function DashboardGallery() {
  const navigate = useNavigate();
  const [saved, setSaved] = useState(() => loadSavedViews());
  const clone = (id: string) => {
    const source = dashboardTemplate(id)!;
    const name = prompt("Private view name", `${source.title} — My view`);
    if (!name) return;
    try {
      const view = cloneTemplate(id, name);
      const next = upsertSavedView(saved, view);
      saveViews(next);
      setSaved(next);
      navigate(`/dashboards/${view.id}`);
    } catch (error) {
      alert((error as Error).message);
    }
  };
  return (
    <div className="page">
      <div className="eyebrow">OPERATIONAL DASHBOARDS / BOUNDED EVIDENCE</div>
      <h1>Operational dashboards</h1>
      <p>
        Built-in dashboards are immutable. Private browser views store
        presentation preferences only and are not shared or server-persisted.
      </p>
      <h2>Built-in</h2>
      <section className="dashboard-gallery">
        {dashboardTemplates.map((x) => (
          <article className="panel" key={x.id}>
            <small>BUILT-IN</small>
            <h3>{x.title}</h3>
            <p>{x.description}</p>
            <p>{x.widgets.length} widgets</p>
            <div className="actions">
              <Link className="button primary" to={`/dashboards/${x.id}`}>
                Open
              </Link>
              <button onClick={() => clone(x.id)}>Clone as private view</button>
            </div>
          </article>
        ))}
      </section>
      <h2>Private browser views</h2>
      {saved.views.length === 0 ? (
        <p>No private views saved in this browser.</p>
      ) : (
        <section className="dashboard-gallery">
          {saved.views.map((x) => (
            <article className="panel" key={x.id}>
              <small>PRIVATE CUSTOMISED VIEW</small>
              <h3>{x.title}</h3>
              <p>
                {x.widgets.length} widgets · modified{" "}
                {new Date(x.modifiedAt).toLocaleString()}
              </p>
              <Link to={`/dashboards/${x.id}`}>Open</Link>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function Widget({
  widget,
  data,
  loading,
  authorised,
  available,
  editing,
  onAction,
  onRemove,
}: {
  widget: DashboardWidgetDefinition;
  data?: CommandCenter;
  loading: boolean;
  authorised: boolean;
  available: boolean;
  editing: boolean;
  onAction: (a: LayoutAction) => void;
  onRemove: () => void;
}) {
  const registration = requireWidget(widget.type);
  let body;
  if (!authorised)
    body = (
      <p role="status">You no longer have permission to view this widget.</p>
    );
  else if (!available)
    body = (
      <p role="status">
        This capability is unavailable or not configured. No provider request
        was made.
      </p>
    );
  else if (loading)
    body = <LoadingSkeleton label={`Loading ${widget.title}…`} />;
  else if (!data)
    body = (
      <p role="alert">
        Evidence is unavailable. Missing evidence is not zero or healthy.
      </p>
    );
  else if (widget.type === "overall-health")
    body = (
      <>
        <HealthBadge
          state={data.data_status.complete ? data.overall_health : "partial"}
        />
        <p>
          {data.data_status.complete
            ? "Bounded estate evidence."
            : "Partial evidence; health is not inferred."}
        </p>
      </>
    );
  else if (widget.type === "pillar-health")
    body = (
      <ul>
        {data.pillars.slice(0, 6).map((x) => (
          <li key={x.id}>
            {x.name}: <HealthBadge state={x.health} />
          </li>
        ))}
      </ul>
    );
  else if (widget.type === "priority-work")
    body = data.priority_items.length ? (
      <ol>
        {data.priority_items.slice(0, 10).map((x) => (
          <li key={x.id}>
            {x.problem} — {x.severity}
          </li>
        ))}
      </ol>
    ) : (
      <p>{registration.emptyMessage}</p>
    );
  else if (widget.type === "source-coverage")
    body = (
      <p className="dashboard-metric">
        {data.data_status.source_coverage == null
          ? "Missing"
          : `${data.data_status.source_coverage}%`}
      </p>
    );
  else if (widget.type === "recent-changes")
    body = data.recent_changes.length ? (
      <ul>
        {data.recent_changes.slice(0, 10).map((x) => (
          <li key={x.id}>
            {x.title} — {x.time}
          </li>
        ))}
      </ul>
    ) : (
      <p>{registration.emptyMessage}</p>
    );
  else
    body = (
      <p>
        Bounded read contract is not enabled for this widget in v1. Open the
        authoritative capability page.
      </p>
    );
  return (
    <article
      className="dashboard-widget panel"
      style={{
        gridColumn: `span ${widget.layout.width}`,
        minHeight: `${widget.layout.height * 4}rem`,
      }}
      aria-labelledby={`${widget.id}-title`}
    >
      <header>
        <h2 id={`${widget.id}-title`}>{widget.title}</h2>
        <small>{registration.displayName}</small>
      </header>
      {body}
      <footer className="actions">
        <Link to={widgetDetailsPath(widget.type)}>Open details</Link>
        {registration.investigation && (
          <Link
            to={buildRoutePath("investigation-workspace") ?? "/investigate"}
          >
            Investigate
          </Link>
        )}
      </footer>
      {editing && (
        <div
          className="widget-controls"
          aria-label={`Layout controls for ${widget.title}`}
        >
          {(
            [
              "left",
              "right",
              "up",
              "down",
              "wider",
              "narrower",
              "taller",
              "shorter",
            ] as LayoutAction[]
          ).map((a) => (
            <button key={a} onClick={() => onAction(a)}>
              {a}
            </button>
          ))}
          <button onClick={onRemove}>Remove</button>
        </div>
      )}
    </article>
  );
}

export function DashboardView() {
  const { dashboardId = "" } = useParams();
  const navigate = useNavigate();
  const context = useProductContext();
  const [envelope, setEnvelope] = useState(() => loadSavedViews());
  const initial =
    dashboardTemplate(dashboardId) ??
    envelope.views.find((x) => x.id === dashboardId);
  const [view, setView] = useState<DashboardDefinition | undefined>(initial);
  const [draft, setDraft] = useState<DashboardDefinition | undefined>();
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState<CommandCenter>();
  const [loading, setLoading] = useState(false);
  const abort = useRef<AbortController>();
  const active = draft ?? view;
  const permitted = useMemo(
    () => new Set(context.identity?.permissions ?? []),
    [context.identity?.permissions],
  );
  const load = useCallback(() => {
    if (!active || !context.tenant || !context.environment) return;
    const needs = active.widgets.some((w) => {
      const r = requireWidget(w.type);
      return (
        r.providerId === "command-center" &&
        (r.permission === "console:read" || permitted.has(r.permission))
      );
    });
    if (!needs) {
      setData(undefined);
      return;
    }
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setLoading(true);
    void api
      .commandCenter(
        context.tenant,
        context.environment,
        timeRangeBounds(context.timeRange),
        controller.signal,
      )
      .then(setData)
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setData(undefined);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [
    active,
    context.environment,
    context.tenant,
    context.timeRange,
    permitted,
  ]);
  // The effect deliberately starts an abortable external evidence synchronisation.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => load(), [load, context.refreshGeneration]);
  useEffect(() => {
    new WatchlistStore().read(
      contextFingerprint(context.tenant, context.environment),
    );
    return () => abort.current?.abort();
  }, [context.environment, context.tenant]);
  if (!active)
    return (
      <div className="page">
        <h1>Dashboard not found</h1>
        <Link to="/dashboards">Return to dashboards</Link>
      </div>
    );
  const isPrivate = active.owner === "private";
  const updateWidget = (id: string, a: LayoutAction) =>
    setDraft(
      (v) =>
        v && {
          ...v,
          widgets: v.widgets.map((w) =>
            w.id === id ? { ...w, layout: adjustLayout(w, a) } : w,
          ),
        },
    );
  const begin = () => {
    if (!isPrivate) {
      const name = prompt("Private view name", `${active.title} — My view`);
      if (name) {
        const cloned = cloneTemplate(active.id, name);
        const next = upsertSavedView(envelope, cloned);
        saveViews(next);
        navigate(`/dashboards/${cloned.id}`);
      }
      return;
    }
    setDraft(structuredClone(active));
    setEditing(true);
  };
  const save = () => {
    if (!draft) return;
    const nextView = {
      ...draft,
      modifiedAt: new Date().toISOString(),
    } as SafeSavedView;
    const next = upsertSavedView(envelope, nextView);
    saveViews(next);
    setEnvelope(next);
    setView(nextView);
    setDraft(undefined);
    setEditing(false);
  };
  return (
    <div className="page">
      <Link to="/dashboards">← All dashboards</Link>
      <div className="page-title">
        <div>
          <small>
            {isPrivate ? "PRIVATE BROWSER VIEW" : "BUILT-IN IMMUTABLE"}
          </small>
          <h1>{active.title}</h1>
          <p>{active.description}</p>
        </div>
        <div className="actions">
          {editing ? (
            <>
              <button
                onClick={() => {
                  setDraft(undefined);
                  setEditing(false);
                }}
              >
                Cancel
              </button>
              <button className="primary" onClick={save}>
                Save
              </button>
              <button
                onClick={() =>
                  setDraft(resetSavedView(active as SafeSavedView))
                }
              >
                Reset to template
              </button>
            </>
          ) : (
            <button onClick={begin}>
              {isPrivate ? "Edit view" : "Clone as private view"}
            </button>
          )}
        </div>
      </div>
      {!data && !loading && (
        <DataStatusBanner state="partial">
          Some capability widgets are link-only because no audited bounded
          aggregate contract exists.
        </DataStatusBanner>
      )}
      <div className="dashboard-filter-bar" aria-label="Dashboard filters">
        <strong>Shared context</strong>
        <span>{context.timeRange}</span>
        <span>Filters are applied only by declaring widgets.</span>
      </div>
      <section className="dashboard-grid" aria-live="polite">
        {active.widgets.map((w) => {
          const r = requireWidget(w.type);
          const authorised =
            r.permission === "console:read" || permitted.has(r.permission);
          const available =
            (context.identity?.capabilities?.[r.capabilityId] ??
              "available") === "available";
          return (
            <Widget
              key={w.id}
              widget={w}
              data={r.providerId === "command-center" ? data : undefined}
              loading={loading && r.providerId === "command-center"}
              authorised={authorised}
              available={available}
              editing={editing}
              onAction={(a) => updateWidget(w.id, a)}
              onRemove={() =>
                setDraft(
                  (v) =>
                    v && {
                      ...v,
                      widgets: v.widgets.filter((x) => x.id !== w.id),
                    },
                )
              }
            />
          );
        })}
      </section>
      {editing && (
        <div className="panel">
          <h2>Add widget</h2>
          <select
            aria-label="Widget to add"
            onChange={(e) => {
              const type = e.target.value;
              if (!type || !draft || draft.widgets.length >= 20) return;
              const r = requireWidget(type);
              setDraft({
                ...draft,
                widgets: [
                  ...draft.widgets,
                  {
                    id: `${r.type}-${crypto.randomUUID()}`,
                    type: r.type,
                    title: r.displayName,
                    capabilityId: r.capabilityId,
                    layout: { x: 0, y: 99, width: 4, height: 3 },
                    config: {},
                  },
                ],
              });
              e.target.value = "";
            }}
          >
            <option value="">Choose a supported widget</option>
            {widgetRegistrations.map((r) => (
              <option key={r.type} value={r.type}>
                {r.displayName}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
