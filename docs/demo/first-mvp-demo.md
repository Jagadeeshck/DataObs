# DataObs first-MVP demo

This is a bounded local product walkthrough for version 0.2.0. It is not a
production deployment, security certification, or supported-platform claim.
The `First MVP demo smoke` workflow exercises the same build, seed, proxy, and
verification path in hosted CI; its artifact is explicitly non-certifying.

## Before the session

Use a Docker Compose v2 host with at least 4 CPU, 8 GiB RAM, and 10 GiB free
disk. From a clean checkout:

```bash
cp .env.mvp.example .env.mvp
# Replace both placeholder values with temporary local-only secrets.
./scripts/demo_mvp.sh config
./scripts/demo_mvp.sh up
```

`up` builds the API and Console images, waits for Elasticsearch, applies the
released migration graph, seeds deterministic tenant-isolated Console data, and
verifies the full browser proxy path. It succeeds only after `/readyz`, Console
health, identity context, Command Center, topology, and tenant isolation pass.

Run the verification immediately before presenting:

```bash
./scripts/demo_mvp.sh verify
./scripts/demo_mvp.sh status
```

Open <http://localhost:3000>. Keep `./scripts/demo_mvp.sh logs` available in a
second terminal, but do not display environment files or credentials.

## Ten-minute walkthrough

1. **0:00–1:00 — Scope.** State that this is the local evaluation MVP using
   Elasticsearch 9.5.5, DataObs 0.2.0, and the current 33-migration graph.
2. **1:00–3:00 — Command Center.** Show the seeded `acme-retail / production`
   context and explain that incomplete sources remain explicit rather than being
   rendered as healthy.
3. **3:00–6:00 — Topology.** Open the pathway/topology experience, show the five
   deterministic resources, and follow the critical topic signal into the
   relevant detail view.
4. **6:00–8:00 — Product navigation.** Demonstrate that the Console and API are
   one containerized experience and that browser requests traverse the Nginx
   `/api/` proxy without bypassing tenant context.
5. **8:00–9:00 — Isolation proof.** Run `./scripts/demo_mvp.sh verify`; explain
   that it rejects any `northstar` fixture in the active tenant responses.
6. **9:00–10:00 — Honest close.** Identify unconfigured capabilities and explain
   that hosted certification, production OIDC/TLS, HA, backup/restore, and
   supported-platform authorization are later gates.

## Recovery during the session

```bash
./scripts/demo_mvp.sh status
./scripts/demo_mvp.sh logs
./scripts/demo_mvp.sh verify
```

If verification fails, stop the walkthrough rather than presenting stale or
cross-tenant data. Restart with `./scripts/demo_mvp.sh down` followed by
`./scripts/demo_mvp.sh up`. This preserves the Elasticsearch volume and the seed
is replay-safe because it uses deterministic document IDs. To intentionally
discard local evaluation data, run the Compose `down --volumes` command from
the first-MVP development guide.

## End of session

```bash
./scripts/demo_mvp.sh down
```

Do not claim `GO`, production readiness, independent verification, or platform
support based on this demo. Current product truth remains `NO_GO`, security
`INCOMPLETE`, and supported platforms `[]`.

