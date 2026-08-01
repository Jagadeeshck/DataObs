import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DataStatusBanner } from "../../components/Evidence";
import { useProductContext } from "../../state/context";
import { onboardingStorageKey, redactOnboardingProgress } from "./progress";

const goals = [
  {
    id: "freshness",
    name: "Monitor data freshness",
    integrations: ["Data stores", "Orchestration"],
  },
  {
    id: "quality",
    name: "Monitor data quality",
    integrations: ["Data stores", "Transformation"],
  },
  {
    id: "jobs",
    name: "Observe jobs and runs",
    integrations: ["Orchestration"],
  },
  {
    id: "lineage",
    name: "Investigate lineage",
    integrations: ["Orchestration", "Transformation"],
  },
  { id: "kafka", name: "Monitor Kafka streams", integrations: ["Streaming"] },
  {
    id: "incidents",
    name: "Track incidents",
    integrations: ["Incident management"],
  },
  {
    id: "pathways",
    name: "Understand end-to-end pathways",
    integrations: ["Streaming", "Orchestration", "Data stores"],
  },
] as const;
export function Onboarding() {
  const { tenant, environment } = useProductContext();
  const saved = (() => {
    try {
      return JSON.parse(
        localStorage.getItem(onboardingStorageKey) ?? "null",
      ) as { step?: number; goals?: string[] } | null;
    } catch {
      return null;
    }
  })();
  const [step, setStep] = useState(saved?.step ?? 0);
  const [selected, setSelected] = useState<string[]>(saved?.goals ?? []);
  const [validation, setValidation] = useState("");
  const recommendations = useMemo(
    () => [
      ...new Set(
        goals
          .filter((goal) => selected.includes(goal.id))
          .flatMap((goal) => goal.integrations),
      ),
    ],
    [selected],
  );
  const persist = (nextStep: number, nextGoals = selected) => {
    localStorage.setItem(
      onboardingStorageKey,
      JSON.stringify(
        redactOnboardingProgress({ step: nextStep, goals: nextGoals }),
      ),
    );
    setStep(nextStep);
  };
  const next = () => {
    if (step === 1 && !selected.length) {
      setValidation("Select at least one observability goal.");
      return;
    }
    setValidation("");
    persist(Math.min(step + 1, 3));
  };
  return (
    <div className="page onboarding">
      <div className="eyebrow">GUIDED SETUP / STEP {step + 1} OF 4</div>
      <h1>
        {
          [
            "Welcome to DataObs",
            "Choose observability goals",
            "Review recommended integration categories",
            "Setup ready to continue",
          ][step]
        }
      </h1>
      {step === 0 && (
        <section className="panel">
          <p>
            This browser is using trusted access to tenant{" "}
            <strong>{tenant}</strong> and environment{" "}
            <strong>{environment}</strong>. Those values cannot be entered
            arbitrarily.
          </p>
          <DataStatusBanner state="partial">
            Beta 1 stores only non-sensitive step and goal selections locally.
            Never enter credentials here.
          </DataStatusBanner>
        </section>
      )}
      {step === 1 && (
        <fieldset>
          <legend>What would you like to observe?</legend>
          {goals.map((goal) => (
            <label className="goal" key={goal.id}>
              <input
                type="checkbox"
                checked={selected.includes(goal.id)}
                onChange={(event) => {
                  const nextGoals = event.target.checked
                    ? [...selected, goal.id]
                    : selected.filter((value) => value !== goal.id);
                  setSelected(nextGoals);
                  localStorage.setItem(
                    onboardingStorageKey,
                    JSON.stringify(
                      redactOnboardingProgress({ step, goals: nextGoals }),
                    ),
                  );
                }}
              />
              {goal.name}
            </label>
          ))}
        </fieldset>
      )}
      {validation && (
        <p role="alert" className="validation">
          {validation}
        </p>
      )}
      {step === 2 && (
        <section className="panel">
          <p>
            These categories are recommended deterministically from your
            selected goals:
          </p>
          <ul>
            {recommendations.map((item) => (
              <li key={item}>
                <strong>{item}</strong> — required by{" "}
                {goals
                  .filter(
                    (goal) =>
                      selected.includes(goal.id) &&
                      goal.integrations.includes(item as never),
                  )
                  .map((goal) => goal.name)
                  .join(", ")}
              </li>
            ))}
          </ul>
          <p>
            Permission, secret-reference, connectivity-test, scope, and
            telemetry details depend on Team 4 integration metadata.
          </p>
        </section>
      )}
      {step === 3 && (
        <section className="panel">
          <DataStatusBanner state="not_configured">
            Goals are saved locally. Provider setup remains not configured until
            the integrations contract accepts a backend-managed credential
            reference.
          </DataStatusBanner>
          <Link className="button-link" to="/integrations">
            Open integrations
          </Link>{" "}
          <Link className="button-link" to="/">
            Open Command Center
          </Link>
        </section>
      )}
      <div className="onboarding-actions">
        <button
          disabled={step === 0}
          onClick={() => persist(Math.max(0, step - 1))}
        >
          Back
        </button>
        {step < 3 && (
          <button className="primary" onClick={next}>
            Continue
          </button>
        )}
        <Link to="/">Exit onboarding</Link>
      </div>
    </div>
  );
}
