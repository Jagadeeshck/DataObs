import { useEffect, useState } from "react";
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
  const [data, setData] = useState<Record<string, unknown>>();
  const [error, setError] = useState<string>();
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
      .then(setData)
      .catch(() => setError(`${tab} evidence is unavailable in this scope.`));
    return () => controller.abort();
  }, [tab, tenant, environment, productId]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading {tab.toLowerCase()}…</p>;
  const items = (data.items ?? data.edges ?? []) as Array<
    Record<string, unknown>
  >;
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
      {data.next_cursor ? <button type="button">Load next page</button> : null}
    </div>
  );
}
