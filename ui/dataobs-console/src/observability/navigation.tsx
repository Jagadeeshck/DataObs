import { useEffect, useRef } from "react";
import { trace } from "@opentelemetry/api";
import { useLocation, useNavigationType } from "react-router-dom";
import { routeForPath } from "../app/routes";
import { safeAttributes } from "./attributePolicy";
import { diagnostics } from "./diagnostics";
import { finishStartup } from "./bootstrap";

export function NavigationTelemetry() {
  const location = useLocation();
  const navigationType = useNavigationType();
  const previousKey = useRef<string>();
  useEffect(() => {
    const route = routeForPath(location.pathname);
    const routeId = route?.id ?? "not-found";
    diagnostics.update({ currentRouteId: routeId });
    if (previousKey.current === location.key) return;
    previousKey.current = location.key;
    const span = trace
      .getTracer("dataobs-console")
      .startSpan(`console.route.${routeId}`, {
        attributes: safeAttributes({
          "dataobs.console.route_id": routeId,
          "dataobs.console.capability_id": route?.capabilityId ?? "not-found",
          "dataobs.console.owner_team": route?.owner ?? "team-5",
          "dataobs.console.navigation_type": navigationType.toLowerCase(),
        }),
      });
    requestAnimationFrame(() => {
      span.addEvent("route.rendered");
      span.end();
      finishStartup();
    });
  }, [location.key, location.pathname, navigationType]);
  return null;
}
