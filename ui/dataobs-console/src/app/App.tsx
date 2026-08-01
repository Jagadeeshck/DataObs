import { lazy, Suspense, type ComponentType, type ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { ProductContextProvider } from "../state/context";
import { NotFound, RouteBoundary } from "./RouteStates";
import { consoleRoutes } from "./routes";
import { NavigationTelemetry } from "../observability";
import { useProductContext } from "../state/context";

function PermissionGate({
  permission,
  children,
}: {
  permission?: string;
  children: ReactNode;
}) {
  const { identity } = useProductContext();
  const location = useLocation();
  const allowed =
    !permission ||
    permission === "console:read" ||
    identity?.permissions.includes(permission);
  return allowed ? (
    children
  ) : (
    <Navigate to="/unauthorised" replace state={{ from: location.pathname }} />
  );
}

const lazyComponents = new Map<string, ComponentType>();

function componentFor(route: (typeof consoleRoutes)[number]) {
  let component = lazyComponents.get(route.id);
  if (!component) {
    component = lazy(route.loader);
    lazyComponents.set(route.id, component);
  }
  const Component = component;
  return (
    <RouteBoundary routeName={route.name}>
      <Suspense
        fallback={
          <p className="route-loading" role="status">
            {route.loadingLabel}
          </p>
        }
      >
        <Component />
      </Suspense>
    </RouteBoundary>
  );
}

export function App() {
  const publicRoutes = consoleRoutes.filter((route) => !route.protected);
  const protectedRoutes = consoleRoutes.filter((route) => route.protected);

  return (
    <ProductContextProvider>
      <BrowserRouter>
        <NavigationTelemetry />
        <Routes>
          {publicRoutes.map((route) => (
            <Route
              key={route.id}
              path={route.path}
              element={componentFor(route)}
            />
          ))}
          <Route element={<AppShell />}>
            {protectedRoutes.map((route) => (
              <Route
                key={route.id}
                path={route.path}
                element={
                  <PermissionGate permission={route.requiredPermission}>
                    {componentFor(route)}
                  </PermissionGate>
                }
              />
            ))}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
