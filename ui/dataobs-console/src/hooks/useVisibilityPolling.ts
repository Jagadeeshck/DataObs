import { useCallback, useEffect, useRef } from "react";

export function useVisibilityPolling(refresh: () => void, intervalMs: number) {
  const latest = useRef(refresh);
  useEffect(() => {
    latest.current = refresh;
  }, [refresh]);
  const manualRefresh = useCallback(() => latest.current(), []);
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") latest.current();
    };
    const id = window.setInterval(tick, intervalMs);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [intervalMs]);
  return manualRefresh;
}
