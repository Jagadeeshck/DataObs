/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../api/common";

export function useQualityRequest<T>(
  request: (signal: AbortSignal) => Promise<T>,
  dependencies: unknown[],
) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    request(controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(
            reason instanceof ApiError
              ? `${reason.status}: ${reason.message}`
              : "Quality evidence is unavailable",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // The caller owns the stable scope dependencies; request closures intentionally change every render.
  }, [revision, ...dependencies]);
  return { data, error, loading, refresh };
}
