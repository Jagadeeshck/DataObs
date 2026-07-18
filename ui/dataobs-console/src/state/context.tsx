import { createContext, useContext, useState, type ReactNode } from "react";
type ContextValue = {
  tenant: string;
  environment: string;
  setTenant: (v: string) => void;
  setEnvironment: (v: string) => void;
};
const ProductContext = createContext<ContextValue | null>(null);
export function ProductContextProvider({ children }: { children: ReactNode }) {
  const params = new URLSearchParams(location.search);
  const [tenant, setTenantState] = useState(
    params.get("tenant") ?? "acme-retail",
  );
  const [environment, setEnvironmentState] = useState(
    params.get("environment") ?? "production",
  );
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(location.search);
    next.set(key, value);
    history.replaceState({}, "", `${location.pathname}?${next}`);
  };
  const value = {
    tenant,
    environment,
    setTenant: (v: string) => {
      setTenantState(v);
      update("tenant", v);
    },
    setEnvironment: (v: string) => {
      setEnvironmentState(v);
      update("environment", v);
    },
  };
  return (
    <ProductContext.Provider value={value}>{children}</ProductContext.Provider>
  );
}
export function useProductContext() {
  const value = useContext(ProductContext);
  if (!value) throw new Error("Product context unavailable");
  return value;
}
