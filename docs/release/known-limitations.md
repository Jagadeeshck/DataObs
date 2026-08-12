# Known limitations — first supported platform closure v1

The `0.2.0-rc.1` evaluation is **NO_GO** and there is currently no supported
platform profile.

* Development, standard-ha and production-ha topologies remain unvalidated.
* Small, medium and large capacity profiles lack retained exact-SHA measurements.
* Cloud, multi-zone, cross-cluster and cross-region topologies are unsupported.
* Secured Elasticsearch 9.4.2 and OIDC PKCE/JWKS behavior lack hosted evidence.
* Backup/restore and dependency recovery require protected disposable execution;
  DR procedures contain manual/operator boundaries and have no measured RPO/RTO.
* There is no supported predecessor. N-1 guarantees can begin only after a first
  supported release; rollback is classified `rollback_not_applicable_first_release`.
* Browser/accessibility and provider-specific capability certification have gaps.
* Functional simulation cannot satisfy hosted HA, recovery, isolation, or DR.
* Candidate images/chart, SBOM, scan/license reports, provenance, signatures and
  install-from-artifact evidence do not exist because eligibility failed before
  the protected build/publication boundary.
* A platform support decision, when one exists, will not certify every Team 1–5
  integration or capability. Capability states remain independently governed.
