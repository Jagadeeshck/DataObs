import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";

type Props = {
  tab: string;
  tenant: string;
  environment: string;
  productId: string;
};

export function ProductEvidenceTabs({
  tab,
  tenant,
  environment,
  productId,
}: Props) {
  type EvidenceItem = {
    membership_id?: string;
    operation_id?: string;
    upstream_product_id?: string;
    entity_id?: string;
    state?: string;
    outcome?: string;
    relationship?: string;
    observed_at?: string;
    occurred_at?: string;
  };
  type EvidencePage = {
    items?: EvidenceItem[];
    edges?: EvidenceItem[];
    truncated?: boolean;
    next_cursor?: string;
  };
  const [data, setData] = useState<EvidencePage>();
  const [error, setError] = useState<string>();
  const [loadingMore, setLoadingMore] = useState(false);
  const statusRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const section: Record<string, string> = {
      Members: "members",
      Lineage: "dependencies/upstream?depth=1",
      Dependencies: "dependencies",
      Revisions: "revisions",
    };
    if (!section[tab]) return;
    const controller = new AbortController();
    api
      .dataProductSection(
        tenant,
        environment,
        productId,
        section[tab],
        controller.signal,
      )
      .then((value) => setData(value as EvidencePage))
      .catch(() => setError(`${tab} evidence is unavailable in this scope.`));
    return () => controller.abort();
  }, [tab, tenant, environment, productId]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading {tab.toLowerCase()}…</p>;
  const items = data.items ?? data.edges ?? [];
  const loadNext = async () => {
    if (!data.next_cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const next = (await api.dataProductSection(
        tenant,
        environment,
        productId,
        `${tab === "Members" ? "members" : tab.toLowerCase()}?cursor=${encodeURIComponent(data.next_cursor)}`,
      )) as EvidencePage;
      setData({
        ...next,
        items: [...items, ...(next.items ?? next.edges ?? [])],
      });
      statusRef.current?.focus();
    } finally {
      setLoadingMore(false);
    }
  };
  return (
    <div>
      {Boolean(data.truncated) && (
        <p role="status">
          Results are truncated by the configured graph budget.
        </p>
      )}
      {items.length === 0 ? (
        <p>No {tab.toLowerCase()} evidence is available.</p>
      ) : (
        <table>
          <caption>{tab} evidence</caption>
          <thead>
            <tr>
              <th scope="col">Identifier</th>
              <th scope="col">State</th>
              <th scope="col">Observed</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr
                key={String(
                  item.membership_id ??
                    item.operation_id ??
                    item.upstream_product_id ??
                    index,
                )}
              >
                <td>
                  {String(
                    item.entity_id ??
                      item.upstream_product_id ??
                      item.operation_id ??
                      "Unknown",
                  )}
                </td>
                <td>
                  {String(
                    item.state ??
                      item.outcome ??
                      item.relationship ??
                      "available",
                  )}
                </td>
                <td>
                  {String(item.observed_at ?? item.occurred_at ?? "Unknown")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p ref={statusRef} role="status" tabIndex={-1}>
        {loadingMore
          ? "Loading more evidence…"
          : `${items.length} records loaded.`}
      </p>
      {data.next_cursor ? (
        <button type="button" disabled={loadingMore} onClick={loadNext}>
          Load next page
        </button>
      ) : null}
    </div>
  );
}
