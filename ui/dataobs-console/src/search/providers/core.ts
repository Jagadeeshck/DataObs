import {
  api,
  qualityApi,
  type Asset,
  type DataProduct,
  type MonitorDefinition,
} from "../../api";
import { classifyMatch } from "../ranking";
import type { SearchProvider, SearchResult } from "../types";
const base = {
  minimumQueryLength: 2,
  maximumResults: 5,
  timeoutMs: 1500,
  isAvailable: () => true,
} as const;
const result = (
  provider: SearchProvider,
  entityType: SearchResult["entityType"],
  id: string,
  label: string,
  routeId: string,
  parameter: string,
  query: string,
  extras: Partial<SearchResult> = {},
): SearchResult => ({
  key: `${provider.id}:${id}`,
  entityType,
  capabilityId: provider.capabilityId,
  ownerTeam: provider.ownerTeam,
  identifier: id,
  label,
  routeId,
  routeParameters: { [parameter]: id },
  requiredPermission: provider.requiredPermission,
  providerId: provider.id,
  match: classifyMatch(query, id, label),
  ...extras,
});
export const assetProvider: SearchProvider = {
  ...base,
  id: "assets",
  label: "Assets",
  capabilityId: "assets",
  ownerTeam: "team-2",
  entityTypes: ["asset"],
  requiredPermission: "assets:read",
  async search(r, signal) {
    const data = await api.assets(
      r.context.tenant,
      r.context.environment,
      r.query,
      signal,
    );
    return {
      results: data.items
        .slice(0, r.limit)
        .map((x: Asset) =>
          result(
            assetProvider,
            "asset",
            x.id,
            x.name || x.id,
            "asset-360",
            "assetId",
            r.query,
            { health: x.health },
          ),
        ),
    };
  },
};
export const dataProductProvider: SearchProvider = {
  ...base,
  id: "data-products",
  label: "Data products",
  capabilityId: "data-products",
  ownerTeam: "team-2",
  entityTypes: ["data_product"],
  requiredPermission: "data_products:read",
  async search(r, signal) {
    const q = new URLSearchParams({
      search: r.query,
      limit: String(r.limit),
      sort: "name",
    });
    const data = await api.dataProducts(
      r.context.tenant,
      r.context.environment,
      q,
      signal,
    );
    return {
      results: data.items.map((x: DataProduct) =>
        result(
          dataProductProvider,
          "data_product",
          x.id,
          x.name,
          "data-product-360",
          "productId",
          r.query,
          { secondaryLabel: x.domain },
        ),
      ),
    };
  },
};
export const monitorProvider: SearchProvider = {
  ...base,
  id: "monitors",
  label: "Monitors",
  capabilityId: "quality",
  ownerTeam: "team-2",
  entityTypes: ["monitor"],
  requiredPermission: "quality:read",
  async search(r, signal) {
    const q = new URLSearchParams({
      search: r.query,
      limit: String(r.limit),
      sort: "name",
    });
    const response = await qualityApi.monitors(
      r.context.tenant,
      r.context.environment,
      q,
      signal,
    );
    return {
      requestId: response.requestId,
      results: response.data.items.map((x: MonitorDefinition) =>
        result(
          monitorProvider,
          "monitor",
          x.id,
          x.name,
          "monitor-360",
          "monitorId",
          r.query,
          { health: x.state },
        ),
      ),
    };
  },
};
