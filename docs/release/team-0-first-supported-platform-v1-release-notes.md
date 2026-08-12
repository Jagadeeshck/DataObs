# DataObs 0.2.0-rc.1 evaluation notes

This is a **NO_GO evaluation record**, not a published release or support
statement. The candidate source includes the external-Elasticsearch Helm
package, OIDC/RBAC and tenant enforcement, operational backup/restore tooling,
platform lifecycle/runtime work, and terminal migration
`0030_team1_multi_broker_messaging_runtime`.

The intended platform target is Kubernetes 1.30.x, Elasticsearch 9.4.2, Python
3.13, Node 22, external OIDC Authorization Code + PKCE S256, and externally
managed Elasticsearch. These requirements remain unvalidated. Elasticsearch is
never packaged in the chart.

There is no supported predecessor, so no upgrade promise is made. Helm rollback
never reverses Elasticsearch migrations. Breaking-change and migration review
must be repeated against immutable candidate artifacts. See `known-limitations.md`
for hosted, HA/capacity, browser, provider, recovery and supply-chain gaps.
