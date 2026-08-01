import { useEffect, useRef } from "react";
export function useTenantReset(
  tenant: string,
  environment: string,
  reset: () => void,
) {
  const previous = useRef([tenant, environment]);
  useEffect(() => {
    if (previous.current[0] !== tenant || previous.current[1] !== environment) {
      previous.current = [tenant, environment];
      reset();
    }
  }, [tenant, environment, reset]);
}
