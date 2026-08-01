import { Component, type ReactNode } from "react";
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

type BoundaryState = { error?: Error };
export class RouteBoundary extends Component<
  { children: ReactNode; routeName: string },
  BoundaryState
> {
  state: BoundaryState = {};
  static getDerivedStateFromError(error: Error): BoundaryState {
    return { error };
  }
  componentDidCatch() {
    /* reporting is supplied by the host */
  }
  render() {
    if (!this.state.error) return this.props.children;
    const chunkFailure = /chunk|module|import/i.test(this.state.error.message);
    return (
      <section className="route-state" role="alert">
        <h1>{this.props.routeName} could not be loaded</h1>
        <p>
          {chunkFailure
            ? "A Console update may be available."
            : "This capability is temporarily unavailable."}
        </p>
        <button onClick={() => this.setState({ error: undefined })}>
          Retry
        </button>{" "}
        {chunkFailure && (
          <button onClick={() => location.reload()}>Reload Console</button>
        )}
      </section>
    );
  }
}
