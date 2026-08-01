import { lazy, Suspense, type ComponentType } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { ProductContextProvider } from "../state/context";
import { NotFound, RouteBoundary } from "./RouteStates";
import { consoleRoutes } from "./routes";

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
            Loading {route.name}…
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
                element={componentFor(route)}
              />
            ))}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
