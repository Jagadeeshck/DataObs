import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { visibleRoutes } from "../../app/routes";
import { useProductContext } from "../../state/context";
import { readRecent } from "./recent";

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
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle)
      return readRecent(tenant, environment).map((item) => ({
        id: item.route,
        name: item.label,
        path: item.route,
        detail: `Recent ${item.entityType}`,
      }));
    return visibleRoutes(identity?.permissions ?? [])
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
  }, [environment, identity?.permissions, query, tenant]);
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
    const result = results[active];
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
                results[active] ? `quick-${results[active].id}` : undefined
              }
              placeholder="Search Console pages"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActive(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") close();
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActive((value) => Math.min(value + 1, results.length - 1));
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActive((value) => Math.max(value - 1, 0));
                }
                if (event.key === "Enter") select();
              }}
            />
            <p className="sr-only" role="status">
              {results.length} results
            </p>
            <ul id="quick-find-results" role="listbox">
              {results.map((result, index) => (
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
            {!results.length && (
              <p>
                No matching Console pages. Entity search is unavailable until
                bounded APIs are provided.
              </p>
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
