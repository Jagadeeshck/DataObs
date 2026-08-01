import { Component, type ReactNode } from "react";
import { Link, useRouteError } from "react-router-dom";
import { captureError } from "../observability";
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
  private heading = { current: null as HTMLHeadingElement | null };
  componentDidCatch(error: Error) {
    captureError(
      error,
      /chunk|module|import/i.test(error.message)
        ? "chunk-load"
        : "react-render",
      this.props.routeName,
    );
    queueMicrotask(() => this.heading.current?.focus());
  }
  render() {
    if (!this.state.error) return this.props.children;
    const chunkFailure = /chunk|module|import/i.test(this.state.error.message);
    return (
      <section className="route-state" role="alert" aria-live="assertive">
        <h1
          ref={(element) => {
            this.heading.current = element;
          }}
          tabIndex={-1}
        >
          {this.props.routeName} could not be loaded
        </h1>
        <p>
          {chunkFailure
            ? "A Console update may be available."
            : "This capability is temporarily unavailable."}
        </p>
        <button
          onClick={() => {
            captureError(
              new Error("recovery"),
              "recovery-retry",
              this.props.routeName,
            );
            this.setState({ error: undefined });
          }}
        >
          Retry
        </button>{" "}
        {chunkFailure && (
          <button onClick={() => location.reload()}>Reload Console</button>
        )}{" "}
        <Link to="/">Return to Command Center</Link>
      </section>
    );
  }
}
