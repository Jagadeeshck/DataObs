/**
 * Team 5-owned asset-catalog search client.
 *
 * Consumes the existing bounded `/api/v1/assets` contract (Team 2-owned endpoint)
 * and normalises it into a catalog-browse shape with an explicit, absence-preserving
 * fetch state. When the richer Team 2 asset-search endpoint and the Team 0 `0035`
 * semantic-search mapping land, only the transport in `fetchCatalogPage` changes;
 * the groundwork ranking/facet layer in `search/catalog.ts` and the UI stay put.
 *
 * Honesty contract (distinct states, never collapsed into one another):
 * - "loading"      — request in flight.
 * - "measured_zero"— endpoint answered, zero assets match. A real, trustworthy zero.
 * - "ready"        — endpoint answered with one or more assets.
 * - "not_configured"/"unavailable"/"stale"/"partial"/"unknown" — carried through
 *   from the backend data_status; shown separately from a measured zero.
 * - "error"        — transport failed; surfaced with a retry, never shown as zero.
 */
import { api, ApiError, type Asset } from "./index";
import type { DataStatus } from "./common";

export interface CatalogPage {
  items: Asset[];
  nextCursor: string | null;
  /** Backend evidence state; absent/partial/stale stay distinct from a real zero. */
  dataStatus: DataStatus;
  warnings: string[];
}

export type CatalogError = {
  message: string;
  status?: number;
  requestId?: string;
};

export interface CatalogQuery {
  tenant: string;
  environment: string;
  search?: string;
  assetType?: string;
  cursor?: string;
}

const normaliseDataStatus = (value: string | undefined): DataStatus => {
  switch (value) {
    case "complete":
    case "partial":
    case "stale":
    case "not_configured":
    case "unknown":
    case "unavailable":
      return value;
    default:
      return "unknown";
  }
};

/**
 * Fetch one bounded page of catalog assets. Never throws for the caller: transport
 * failures resolve to a CatalogError so the UI can keep a loaded/empty/error state
 * strictly separate. Aborts propagate as a rejection so React can ignore them.
 */
export async function fetchCatalogPage(
  query: CatalogQuery,
  signal?: AbortSignal,
): Promise<{ page: CatalogPage } | { error: CatalogError }> {
  try {
    const response = await api.assets(
      query.tenant,
      query.environment,
      query.search ?? "",
      signal,
      query.cursor ?? "",
      query.assetType ?? "",
    );
    return {
      page: {
        items: response.items ?? [],
        nextCursor: response.next_cursor ?? null,
        dataStatus: normaliseDataStatus(response.data_status),
        warnings: response.warnings ?? [],
      },
    };
  } catch (cause) {
    if (signal?.aborted) throw cause;
    if (cause instanceof ApiError)
      return {
        error: {
          message:
            cause.status === 404
              ? "Asset catalog search is not available in this environment yet."
              : "The asset catalog could not be loaded.",
          status: cause.status,
          requestId: cause.requestId,
        },
      };
    return { error: { message: "The asset catalog could not be loaded." } };
  }
}
