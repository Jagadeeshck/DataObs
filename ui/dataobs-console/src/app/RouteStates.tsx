import { Component, type ReactNode } from "react";
import { Link } from "react-router-dom";
export function NotFound() {
  return (
    <main className="route-state" id="main-content">
      <h1>Page not found</h1>
      <p>The requested Console route is not available.</p>
      <Link to="/">Return to Command Center</Link>
    </main>
  );
}
export class RouteBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    /* The telemetry adapter records sanitized route failures when configured. */
  }
  render() {
    return this.state.failed ? (
      <main className="route-state" id="main-content">
        <h1>This page could not be displayed</h1>
        <p role="alert">
          A route-level error was contained. No other Console data was affected.
        </p>
        <button onClick={() => this.setState({ failed: false })}>
          Retry page
        </button>
        <Link to="/">Return to Command Center</Link>
      </main>
    ) : (
      this.props.children
    );
  }
}
