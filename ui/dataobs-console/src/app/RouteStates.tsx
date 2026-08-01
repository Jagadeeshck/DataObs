import { Link, useRouteError } from "react-router-dom";
export function NotFound() {
  return (
    <main className="route-state" id="main-content">
      <h1>Page not found</h1>
      <p>The requested Console route is not available.</p>
      <Link to="/">Return to Command Center</Link>
    </main>
  );
}
export function RouteError() {
  const error = useRouteError();
  return (
    <main className="route-state" id="main-content">
      <h1>This page could not be displayed</h1>
      <p role="alert">
        A route-level error was contained. No other Console data was affected.
      </p>
      <details>
        <summary>Troubleshooting detail</summary>
        <pre>
          {error instanceof Error ? error.message : "Unknown route error"}
        </pre>
      </details>
      <Link to="/">Return to Command Center</Link>
    </main>
  );
}
