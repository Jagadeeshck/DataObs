import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  buildRoutePath,
  visibleRoutes,
  visibleWorkspaces,
} from "../../app/routes";
import {
  SearchController,
  searchProviders,
  type SearchResult,
} from "../../search";
import { useProductContext } from "../../state/context";
import { clearRecentScope, readRecent } from "./recent";

const isTypingTarget = (target: EventTarget | null) =>
  target instanceof HTMLElement &&
  (target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
export function QuickFind() {
  const { identity, tenant, environment } = useProductContext();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const trigger = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const controller = useMemo(() => new SearchController(searchProviders), []);
  const [entities, setEntities] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle)
      return readRecent(tenant, environment).map((item) => ({
        id: item.route,
        name: item.label,
        path: item.route,
        detail: `Recent ${item.entityType}`,
      }));
    const workspaceResults = visibleWorkspaces(identity?.permissions ?? [])
      .filter((workspace) =>
        [workspace.label, workspace.description, ...workspace.keywords]
          .join(" ")
          .toLocaleLowerCase()
          .includes(needle),
      )
      .sort((a, b) =>
        a.label.toLocaleLowerCase() === needle
          ? -1
          : b.label.toLocaleLowerCase() === needle
            ? 1
            : 0,
      )
      .map((workspace) => ({
        id: `workspace-${workspace.id}`,
        name: workspace.label,
        path: workspace.defaultPath,
        detail: `Workspace · ${workspace.description}`,
      }));
    const routeResults = visibleRoutes(identity?.permissions ?? [])
      .filter(
        (route) =>
          route.quickFind &&
          !route.path.includes(":") &&
          [route.name, route.capabilityId, route.group, ...route.aliases]
            .join(" ")
            .toLocaleLowerCase()
            .includes(needle),
      )
      .map((route) => ({
        id: route.id,
        name: route.name,
        path: route.path,
        detail: `${route.group} · ${route.availability.replace("_", " ")}`,
      }));
    return [...workspaceResults, ...routeResults];
  }, [environment, identity?.permissions, query, tenant]);
  useEffect(() => {
    if (!open || query.trim().length < 2) {
      controller.cancel();
      // eslint-disable-next-line react-hooks/set-state-in-effect -- closing or shortening a query invalidates sensitive results immediately
      setEntities([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    const timer = setTimeout(
      () =>
        void controller.search(
          query,
          {
            tenant,
            environment,
            permissions: identity?.permissions ?? [],
            capabilities: identity?.capabilities,
          },
          (snapshot) => {
            setEntities(snapshot.results);
            setSearching(snapshot.searching);
          },
        ),
      250,
    );
    return () => {
      clearTimeout(timer);
      controller.cancel();
    };
  }, [
    controller,
    environment,
    identity?.capabilities,
    identity?.permissions,
    open,
    query,
    tenant,
  ]);
  const combined = useMemo(
    () =>
      [
        ...results,
        ...entities.map((item) => ({
          id: item.key,
          name: item.label,
          path: buildRoutePath(item.routeId, item.routeParameters) ?? "/search",
          detail: `${item.entityType.replaceAll("_", " ")} · ${item.health ?? "Evidence unavailable"}`,
        })),
      ].slice(0, 35),
    [entities, results],
  );
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (
        (event.key === "/" ||
          ((event.ctrlKey || event.metaKey) &&
            event.key.toLowerCase() === "k")) &&
        !isTypingTarget(event.target)
      ) {
        event.preventDefault();
        setOpen(true);
      }
    };
    addEventListener("keydown", handler);
    return () => removeEventListener("keydown", handler);
  }, []);
  useEffect(() => {
    if (open) queueMicrotask(() => input.current?.focus());
  }, [open]);
  const close = () => {
    setOpen(false);
    setQuery("");
    trigger.current?.focus();
  };
  const select = () => {
    const result = combined[active];
    if (result) {
      close();
      navigate(result.path);
    }
  };
  return (
    <>
      <button
        ref={trigger}
        className="quick-find-trigger"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        Quick Find <kbd>⌘ K</kbd>
      </button>
      {open && (
        <div
          className="quick-find-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <section
            className="quick-find"
            role="dialog"
            aria-modal="true"
            aria-labelledby="quick-find-title"
          >
            <h2 id="quick-find-title">Quick Find</h2>
            <input
              ref={input}
              role="combobox"
              aria-expanded="true"
              aria-controls="quick-find-results"
              aria-activedescendant={
                combined[active] ? `quick-${combined[active].id}` : undefined
              }
              placeholder="Search pages and operational entities"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActive(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") close();
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActive((value) =>
                    Math.min(value + 1, combined.length - 1),
                  );
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActive((value) => Math.max(value - 1, 0));
                }
                if (event.key === "Enter") select();
              }}
            />
            <p className="sr-only" role="status">
              {searching
                ? `Searching; ${combined.length} results available`
                : `${combined.length} results`}
            </p>
            <ul id="quick-find-results" role="listbox">
              {combined.map((result, index) => (
                <li
                  id={`quick-${result.id}`}
                  role="option"
                  aria-selected={index === active}
                  key={result.id}
                >
                  <button
                    onMouseEnter={() => setActive(index)}
                    onClick={() => {
                      setActive(index);
                      close();
                      navigate(result.path);
                    }}
                  >
                    <strong>{result.name}</strong>
                    <small>{result.detail}</small>
                  </button>
                </li>
              ))}
            </ul>
            {!combined.length && !searching && (
              <p>
                {query.trim().length < 2
                  ? "Enter at least two characters to search entities."
                  : "No matching pages or entities."}
              </p>
            )}
            {searching && <p>Searching available entity providers…</p>}
            {!query && combined.length > 0 && (
              <button
                onClick={() => {
                  clearRecentScope(tenant, environment);
                  setQuery(" ");
                  queueMicrotask(() => setQuery(""));
                }}
              >
                Clear recent items
              </button>
            )}
            <button
              className="quick-find-close"
              onClick={close}
              aria-label="Close Quick Find"
            >
              ×
            </button>
          </section>
        </div>
      )}
    </>
  );
}
