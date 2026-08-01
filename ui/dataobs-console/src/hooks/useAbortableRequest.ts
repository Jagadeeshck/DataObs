import { useCallback, useEffect, useRef } from "react";
export function useAbortableRequest() {
  const current = useRef<AbortController>();
  useEffect(() => () => current.current?.abort(), []);
  return useCallback(<T>(request: (signal: AbortSignal) => Promise<T>) => {
    current.current?.abort();
    const controller = new AbortController();
    current.current = controller;
    return request(controller.signal);
  }, []);
}
