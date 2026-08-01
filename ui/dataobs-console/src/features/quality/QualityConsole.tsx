import { useSearchParams } from "react-router-dom";
import { QualityOverviewView } from "./QualityOverview";
import { MonitorInventory } from "./MonitorInventory";
import { QualityFindings } from "./QualityFindings";
import { QualityAuxiliary } from "./QualityAuxiliary";
const tabs = [
  "overview",
  "monitors",
  "findings",
  "recommendations",
  "coverage",
  "runtime",
] as const;
export function QualityConsole() {
  const [params, setParams] = useSearchParams();
  const tab = tabs.includes(params.get("tab") as never)
    ? params.get("tab")!
    : "overview";
  const select = (next: string) => {
    const p = new URLSearchParams(params);
    if (next === "overview") p.delete("tab");
    else p.set("tab", next);
    p.delete("cursor");
    setParams(p);
  };
  return (
    <section aria-labelledby="quality-title">
      <header>
        <h1 id="quality-title">Data Quality</h1>
        <p>
          Read-only monitoring evidence, coverage, findings and runtime health.
        </p>
      </header>
      <nav className="tabs" aria-label="Quality sections">
        {tabs.map((t) => (
          <button
            key={t}
            aria-current={tab === t ? "page" : undefined}
            onClick={() => select(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>
      {tab === "overview" ? (
        <QualityOverviewView />
      ) : tab === "monitors" ? (
        <MonitorInventory />
      ) : tab === "findings" ? (
        <QualityFindings />
      ) : (
        <QualityAuxiliary
          section={tab as "recommendations" | "coverage" | "runtime"}
        />
      )}
    </section>
  );
}
