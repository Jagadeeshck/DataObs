# Data Product reconciliation runtime closure

## Final hosted foundation execution after PR #155

- status: **pending**
- baseline `main` SHA: `745d76a63480e5c25a907df27f77bbbeb41a5525`
- execution PR head SHA: pending branch push
- workflow name: `Data Product hosted certification foundation`
- expected six jobs: `data-product-reconciliation-contracts`, `data-product-reconciliation-unit`, `data-product-foundation-elasticsearch`, `data-product-foundation-security`, `data-product-foundation-evidence`, and `data-product-foundation-summary`
- expected artifact: `data-product-foundation-evidence`
- no-run root cause: this execution environment has no GitHub credential, GitHub CLI, or repository API integration and cannot authenticate to the configured GitHub remote; repository and organization Actions settings, workflow runs, checks, artifacts, and review threads therefore cannot be inspected or changed
- repository or organization setting: unverified because the required owner/API access is unavailable
- owner action taken: none; grant this execution environment authenticated repository/Actions access, including workflow-run, artifact, and review-thread APIs, before hosted certification resumes
- time the workflow became visible: pending authenticated draft PR creation and a `pull_request` run
- full reconciliation certified: false
- release readiness: blocked
- capabilities promoted: none

## certify/final-hosted-foundation execution attempt

- owner-operated execution attempt: started 2026-07-23T21:59:00Z

This pending record is execution tracking only. It is not hosted proof, does not permit eligible review-thread
closure, and does not promote any product capability. The next task after genuine final-head hosted foundation
proof remains the complete Data Product mutation fault matrix.

## PR #154 independent-expectation closure and hosted-proof gate

- status: **blocked pending a final-head hosted pull-request execution**
- baseline `main`: `5b45f7ff06a42fd009eb5003b5dc50ad0ffe0319` (PR #154 merge)
- repository access: available through the installed GitHub App; this checkout has no configured Git
  remote or GitHub API/Actions-settings tool, so the missing-run cause cannot be inspected or corrected
  from this execution environment. The precise missing capability is read/write access to repository and
  organization Actions settings plus workflow-run, artifact, and review-thread APIs.
- diagnosed missing-run limitation: repository files are available through the installed GitHub App,
  but this checkout has no configured Git remote, GitHub CLI, credential, Actions-settings API, or
  workflow-run API. Therefore Actions enablement, allowed-actions policy, organization restrictions,
  workflow registration, billing/minutes, approval, and fork policy cannot be distinguished further;
  owner intervention must grant those exact capabilities before the draft can produce hosted proof.
- correction prepared: producer identity remains `DATA_PRODUCT_CERTIFICATION_SHA`, while independent
  expectation accepts only explicit `--expected-sha` or `EXPECTED_HOSTED_SHA`. Producer identity,
  `GITHUB_SHA`, checkout state, and artifact contents cannot satisfy that trust boundary. Mandatory
  hosted verification now fails closed when expectation is absent and rejects self-consistent wrong-SHA
  bundles; full-profile structural verification retains its non-empty profile-aware control policy.
- workflow event / run ID / URL / six job conclusions: pending a real `pull_request` run
- artifact ID/name/retention: pending / `data-product-foundation-evidence` / 30 days
- Elasticsearch version: `9.4.2` required; hosted result pending
- independent final-head verification and manifest SHA-256: pending retained artifact download
- full reconciliation certified: false
- release readiness: blocked
- capabilities promoted: none
- next task: complete the Data Product mutation fault matrix

This local contract work is not hosted proof. The draft must remain unmerged and review threads must
remain unresolved until the exact-final-head retained ZIP passes independent verification.

## PR #152 SHA/profile blocker closure and hosted-proof gate

- status: **blocked pending hosted pull-request execution**
- baseline `main`: `c9f4ceb66975e77376a9acac0e483052658c9e46` (PR #152 merge)
- diagnosed missing-run limitation: repository access is available through the installed GitHub App, but this checkout exposed no Git remote or Actions settings/run API. It therefore could not inspect Actions enablement, policy, registration, billing/minutes, approval, or branch/fork settings.
- correction prepared: producer and evidence jobs share `DATA_PRODUCT_CERTIFICATION_SHA`; GitHub's synthetic pull-request `GITHUB_SHA` remains untouched. Verification dispatches foundation and full-profile requirements explicitly and fails closed for unknown profiles.
- final head SHA / synthetic merge SHA: pending hosted branch / `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` (local regression contrast)
- workflow event / run ID / URL / six job conclusions: pending a real `pull_request` run
- artifact ID/name/retention: pending / `data-product-foundation-evidence` / 30 days
- Elasticsearch version: `9.4.2` required; hosted result pending
- JUnit, seven scenarios, eight controls, sentinel counts, manifest SHA-256, independent verification: pending retained artifact
- full reconciliation certified: false
- release readiness: blocked
- capabilities promoted: none
- next task after hosted proof: complete Data Product mutation fault matrix

The draft PR must remain unmerged and eligible review threads remain unresolved until an exact-final-head
pull-request run succeeds and its retained artifact passes independent verification.

## PR #151 dispatch defect closure and hosted-proof gate

- status: **blocked pending hosted pull-request execution**
- PR #151 merge commit / latest available `main` snapshot: `bf29ef9126cd73978d04bbe7a063a1656a2d79d7`
- diagnosed missing-run cause: the supplied execution environment has no Git remote, GitHub CLI, or GitHub credential, and the repository is not accessible through the unauthenticated GitHub API. Consequently it cannot inspect repository or organization Actions settings, register/push this branch, or observe a pull-request event. This is an external hosted-execution access blocker, not evidence of a runtime failure; it must not be masked by dispatch evidence.
- correction prepared: `workflow_dispatch` now terminates in a diagnostic-only summary. The retained evidence and certification summary jobs are guarded to `pull_request`, and the evidence builder/verifier require explicit pull-request event, head SHA, run ID/URL, and ordered timezone-aware timestamps.
- workflow event / run ID / URL: pending a real `pull_request` run
- six job conclusions: pending
- artifact ID/name/retention: pending / `data-product-foundation-evidence` / 30 days
- Elasticsearch version: `9.4.2` required; hosted result pending
- JUnit summaries, seven scenario results, eight security controls, sentinel counts: hosted result pending
- manifest SHA-256 and independent verifier result: pending artifact download
- migrations `0001`–`0017`: checksum-identical at `bf29ef9`; no migration source or ledger entry is changed by this patch
- full reconciliation certified: false
- release readiness: blocked
- capabilities promoted: none
- next task after hosted foundation proof: complete Data Product mutation fault matrix

Manual dispatch is registration/runtime diagnosis only. It cannot invoke `build_manifest.py`,
upload `data-product-foundation-evidence`, claim retained certification proof, or justify review-thread
closure. PR thread `PRRT_kwDOR7DqAc6TO-q8` remains unresolved until a final-head pull-request artifact
is downloaded and independently verified. No mutation, proposal, dependency, lifecycle, traversal,
API, Product 360, SLO, RCA, or AI-agent thread is eligible for resolution from this local result.

## Hosted foundation execution attempt after PR #149

- status: pending
- baseline main SHA: `5f21ac9d4cc4ffdc728c2c9967468360842eb927`
- workflow name: `Data Product hosted certification foundation`
- expected jobs: `data-product-reconciliation-contracts`, `data-product-reconciliation-unit`, `data-product-foundation-elasticsearch`, `data-product-foundation-security`, `data-product-foundation-evidence`, and `data-product-foundation-summary`
- expected artifact: `data-product-foundation-evidence`
- execution access limitation: this environment has no configured Git remote, no `gh` client, and no GitHub credential; the unauthenticated GitHub API returns `404 Not Found` for `Jagadeeshck/DataObs`, so it cannot push a branch, open a real draft pull request, inspect Actions or review threads, or download retained evidence
- full reconciliation certified: false
- release readiness: blocked
- capabilities promoted: none

> PR #147 made the foundation scenarios materially executable, but its hosted artifact inventory still rejected `migrations.xml`, one security control was reported without exercising the claim mutation path, stale-worker fencing and complete mixed-resource discrimination were not yet proved, and no pull-request-triggered retained proof existed. This PR closes the hosted foundation gate.

Latest main after PR #147: `5b26bf1`. Migrations `0001`–`0017` remain immutable. Release readiness remains **blocked** and this is foundation evidence, not complete reconciliation certification.

| Foundation capability | Current main after PR #147 | Required final behaviour | Unit/contract | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| migration JUnit ownership | produced but unowned | separately owned `migrations.xml` | covered | required | n/a | pending |
| migration JUnit validation | ignored | nonempty, zero failure/error/skip | covered | required | n/a | pending |
| wrong-scope claim mutation denial | reported without mutation | wrong tenant/environment call `claim_operation`; correct scope succeeds | covered | required | required | pending |
| claim takeover | generation only | exact-boundary generation-two takeover | covered | required | n/a | pending |
| stale-worker fencing after takeover | absent | assert/checkpoint/renew/all terminal paths fenced | covered | required | n/a | pending |
| state resource discrimination | states/plans only | filters precede size and stable order | covered | required | n/a | pending |
| plan resource discrimination | partial | plans cannot consume state limit and load by scope | covered | required | n/a | pending |
| result resource discrimination | absent | results cannot consume state limit and load by scope | covered | required | n/a | pending |
| history resource discrimination | absent | history cannot consume state limit and history reads only events | covered | required | n/a | pending |
| legacy-record starvation prevention | absent | legacy envelopes cannot deserialize or consume size | covered | required | n/a | pending |
| realtime claim/checkpoint visibility | partial | realtime GET observes OCC writes without refresh | covered | required | n/a | pending |
| foundation artifact assembly | rejected producer output | empty exact-owned assembly | covered | required | required | pending |
| manifest/hash verification | one JUnit absent | all JUnits, aliases, paths and hashes fail closed | covered | required | required | pending |
| pull-request-triggered run | absent | success on final head SHA | n/a | pending | pending | pending |
| artifact download verification | absent | retained ZIP downloaded and independently verified | n/a | pending | pending | pending |
| review-thread closure | unresolved | only eligible evidence threads receive exact hosted proof | n/a | pending | pending | pending |

After this gate, the next task is the complete Data Product mutation fault matrix (manual membership, proposals, exclusion, dependency, lifecycle, takeover, immutable replay, terminal revisit, CLI, and remaining security). Product capabilities are not promoted.

> PR #144 added typed superseded-edge handling and deterministic evidence infrastructure, but its executing tests still did not produce the required scenario artifacts, the verifier rejected its generated alias manifest, special security reports bypassed commit/version validation, and the real fault and security matrices remained almost entirely unimplemented. This PR closes and proves the final reconciliation gate.

Latest main baseline after PR #144: `864b1fa`. Migrations `0001`–`0017` remain immutable released history. The authoritative manifest is `certification-evidence.json`; `manifest.json` is its byte-identical compatibility alias. Neither manifest may list itself, and the verifier excludes both only after validating their presence and equality. Hosted columns remain pending until a retained successful pull-request run exists.

| Capability | Current main after PR #144 | Required final behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| PR144 scenario-producer P1 | environment variable only | each executable suite emits only its own passed evidence | contract pending | pending | pending | pending |
| PR144 alias-manifest P1 | alias treated as unlisted input | byte-identical alias excluded from artifact inventory | covered | n/a | n/a | pending |
| PR144 special-report P2 | partial report validation | shared schema, SHA, version, timestamps and result validation | covered | n/a | covered | pending |
| migration and mapping matrix | not executed | clean, 0016 upgrade, repeat apply, mapping and legacy compatibility | pending | pending | n/a | pending |
| retry, claim and resource discrimination | unit/query contracts | real UTC boundaries and filters-before-size | partial | pending | pending | pending |
| reservation, membership, proposal and exclusion | memory/unit focused | complete crash recovery and immutable replay | partial | pending | pending | pending |
| dependency recovery, scale, terminal and takeover | one fencing scenario | complete token/chunk/tombstone/scale/takeover matrix | partial | pending | pending | pending |
| lifecycle and terminal revisit | unit focused | all actions, snapshots, immutable replay and repair | partial | pending | pending | pending |
| CLI result and exit contract | unit focused | real operations, filters, bounds and leak checks | partial | pending | pending | pending |
| persistence security and sentinel redaction | one tenant-state test | complete attack matrix and positive sentinel accounting | partial | pending | pending | pending |
| hosted validation and review closure | absent | retained PR-triggered proof before thread resolution | n/a | pending | pending | pending |

Release readiness remains **blocked**. The next milestone remains **Data Product APIs, Product 360, browser/security, and final hosted core certification**.

> PR #143 improved dependency ordering and evidence validation, but no scenario producer generated the required evidence, the real Elasticsearch and security suites remained shallow, a superseded edge race escaped reconciliation, one certification test still failed, and no hosted artifact set existed. This PR executes and proves the complete runtime.

Latest main baseline: `efae25f` (merge of PR #143). Migrations `0001`–`0017` remain immutable released history. Scenario producers, real-stack execution, and hosted proof are tracked separately: local tests never promote a hosted cell. Release readiness remains **blocked**.

| Capability | Current main after PR #143 | Required final behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| PR143 evidence-producer P1 | inventory without producers | executing tests own every artifact; deterministic assembly | covered | pending | pending | pending |
| PR143 superseded-edge P2 | domain exception escaped with claim running | typed race, authenticated newer revision, terminal superseded outcome | covered | pending | pending | pending |
| migration clean/upgrade/repeat and mapping | migration invocation only | clean 0017, upgrade 0016, repeat apply, wrong-type rejection | partial | pending | pending | pending |
| retry and claim-expiry boundaries | query contracts | injected UTC instant and sub-second boundary proof | covered | pending | pending | pending |
| state/history/plan/result discrimination | unit query contracts | filters before size and realtime state reads | covered | pending | pending | pending |
| reservation/manual/proposal/exclusion recovery | memory-focused | complete crash matrix and immutable replay | partial | pending | pending | pending |
| dependency token/chunks/tombstones/results | unit-focused | 201, 1,001, maximum policy, detailed and terminal evidence | covered | pending | pending | pending |
| dependency newer-edge/two-worker fencing | raw consistency error | never overwrite newer edge; terminal superseded; stale-worker denial | covered | pending | pending | pending |
| lifecycle activate/deprecate/archive | unit-focused | crash recovery and immutable revision replay | covered | pending | pending | pending |
| terminal revisit / attempt exhaustion / CLI | unit-focused | repair all terminal evidence and prove exit outcomes | covered | pending | pending | pending |
| persistence security and redaction | memory-focused | real scoped attack matrix and positive sentinel accounting | covered | pending | pending | pending |
| evidence inventory and schemas | generic JSON validation | owned inventory, distinct schemas, JUnit counts, SHA and hashes | covered | pending | pending | pending |
| hosted run and review-thread closure | absent | successful pull_request run with retained proof before resolution | n/a | pending | pending | pending |

The next milestone is **Data Product APIs, Product 360, browser/security, and final hosted core certification**. Product 360, Impact, SLO, reliability, coverage, RCA, agents, and production readiness are explicitly out of scope.

> PR #142 removed duplicate dependency recovery and added chunked repair and workflow scaffolding, but it did not add or run the real fault matrix, did not migrate indices in the new workflow, did not enforce retained evidence, and left edge-ordering, historical-tombstone, immutable-replay, reservation-only, migration, security, and hosted-proof gaps. This PR closes and proves the runtime.

Latest main baseline: `68e21f0` (merge of PR #142). Migrations `0001`–`0017` are immutable released history; this change does not edit them. Release readiness remains **blocked** until the draft pull request has a successful pull-request-triggered Elasticsearch 9.4.2, security, evidence, and thread-resolution run.

| Capability | Current main after PR #142 | Required final behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| dependency edge OCC ordering | blind OCC replacement | revision-order classification and realtime conflict reread | covered | pending | pending | pending |
| historical tombstone handling | all documents required current graph | only current mutation documents require current graph | covered | pending | pending | pending |
| dependency token-only recovery | partial | repair from durable plan | covered | pending | pending | pending |
| partial upserts and tombstones | chunked but untyped | typed, validated 200-edge chunks | covered | pending | pending | pending |
| detailed and generic result completion | partial | immutable create-or-verify before completion | covered | pending | pending | pending |
| 201 and 1,001 dependencies | unit only | complete bounded result | covered | pending | pending | pending |
| maximum graph policy | literal 10,000 | one public maximum; maximum+1 before writes | covered | pending | pending | pending |
| claim renewal and stale-worker fencing | partial | fence every chunk and terminal boundary | covered | pending | pending | pending |
| canonical dependency/lifecycle terminal times | pending event fallback | one durable terminal instant | covered | pending | pending | pending |
| lifecycle immutable revision replay | partial | exact historical revision | covered | pending | pending | pending |
| proposal immutable replay | mutable projection fallback | typed immutable result | partial | pending | pending | pending |
| reservation-only recovery | undefined | deterministic bind-and-continue | partial | pending | pending | pending |
| migration 0017 clean/upgrade/repeat | not hosted | real clean, upgrade and repeat | pending | pending | pending | pending |
| retry and claim-expiry date boundaries | query-shape only | real deterministic UTC boundaries | pending | pending | pending | pending |
| resource discrimination | unit only | resource filters precede size | covered | pending | pending | pending |
| terminal revisit | partial | canonical immutable chain | covered | pending | pending | pending |
| persistence security | memory focused | real Elasticsearch matrix | pending | pending | pending | pending |
| evidence inventory | declared only | executable required inventory | covered | pending | pending | pending |
| hosted manifest | jobs incomplete | four successful inputs and hashed artifacts | pending | pending | pending | pending |
| review-thread closure | unresolved | resolve only with hosted proof | pending | pending | pending | pending |

No hosted cell is promoted by local execution. Scenario JSON must identify the commit and Elasticsearch version, name the tests and assertions, carry redacted references, and report `passed`; JUnit failures, duplicate basenames, absent security/redaction evidence, or failed job conclusions reject the manifest. The next milestone is **Data Product APIs, Product 360, browser/security, and final hosted core certification**.


> PR #141 added initial durable-plan execution, lifecycle revision finalization, pending-proposal delegation, and a mapped retry date. It did not create the detailed dependency result during reconciliation, remove the duplicate dependency recovery implementation, prove canonical terminal evidence, certify migration 0017 against Elasticsearch, expand the real fault matrix or security suite, or produce retained hosted evidence. This PR closes the reconciliation certification gate.

The authoritative dependency path is now `DependencyReplacementReconciliationHandler` →
`DataProductOperationService` → `RecoverableDataProductOperationCoordinator`. The endpoint
does not contain a second recovery implementation. Repairs use 200-edge claim-fenced chunks,
verify the complete edge and tombstone snapshot, and persist the detailed immutable result
before generic completion. Pending event time is the canonical takeover timestamp.

| Capability | Current main after PR #141 | Required final behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| dependency authoritative recovery | duplicate direct recovery | coordinator only | covered | pending | pending | pending |
| dependency product token recovery | partial | OCC target or fail closed | covered | pending | pending | pending |
| dependency partial upsert/tombstone recovery | unbounded | claim-fenced chunks | covered | pending | pending | pending |
| dependency detailed/generic immutable result | detailed result missing | exact create-or-verify | covered | pending | pending | pending |
| dependency terminal revision event | sampled takeover clock | immutable pending-event time | covered | pending | pending | pending |
| dependency complete active/tombstone evidence | IDs only | checksums, counts and graph version | covered | pending | pending | pending |
| dependency >200 / >1,000 completeness | unproved | complete bounded snapshot | covered | pending | pending | pending |
| dependency claim renewal / stale-worker fencing | one unbounded call | renew per chunk; fence terminal writes | covered | pending | pending | pending |
| lifecycle canonical event/revision/replay/crashes | sampled takeover clock | immutable event and revision | covered | pending | pending | pending |
| proposal immutable replay / reservation-only recovery | mutable reconstruction | typed immutable replay | partial | pending | pending | pending |
| manual/exclusion/dependency/lifecycle reservation-only recovery | inconsistent | deterministic bind or expiry | partial | pending | pending | pending |
| retry migration clean/upgrade/repeat/legacy/boundaries | query-shape tests | real date-safe migration matrix | covered | pending | pending | pending |
| operation resource discrimination | unit contract | filter kind before limit | covered | pending | pending | pending |
| terminal result/history/idempotency/state | partial repair | create-or-canonical-verify | covered | pending | pending | pending |
| real persistence security | memory-focused | hosted Elasticsearch matrix | partial | pending | pending | pending |
| hosted manifest / review-thread closure | absent | retained successful evidence | n/a | pending | pending | pending |

No Elasticsearch, security, or hosted cell is marked complete before a successful retained
workflow artifact. Migrations `0001`–`0017` are released history and remain unchanged. Rollback
means stopping reconciliation workers while retaining operation and certification evidence;
it never deletes mapped fields or reindexes data.

> PR #140 wired coordinator entry points and added implementation-level tests, but dependency recovery still did not execute its durable edge plan, lifecycle recovery did not finalize its revision event/snapshot, proposal retries could reject an already-applied pending operation before reconciliation, and retry scheduling queried a flattened keyword as a date. Real Elasticsearch, security, hosted evidence, and inherited thread closure also remained incomplete. This PR closes those blockers and certifies the runtime.

> PR #138 fixed proposal field access, legacy-worker comparison and idempotency binding only. It did not wire mutation services to the shared coordinator, complete dependency/lifecycle repair, implement the real Elasticsearch/security fault matrix, or produce hosted evidence. This PR closes the runtime and certification gate.

> PR #137 added claim-fenced handler mechanics and partial proposal/exclusion repair, but mutation services were not wired to the coordinator, dependency and lifecycle recovery remained incomplete, two P1 defects were introduced, and real Elasticsearch/security/hosted certification remained absent. This PR closes the reconciliation runtime and evidence gate.

> PR #136 added an authoritative service, terminal idempotency contracts and coordinator scaffolding only. The mutation services and concrete handlers still did not apply most missing projections, normal success paths still left generic state pending, and real Elasticsearch/security/hosted certification remained absent. This PR implements and proves the repair runtime.

> PR #135 closed terminal-status replay, result reuse, query filtering, and initial Elasticsearch completion-repair defects only. Proposal, exclusion, dependency and lifecycle handlers still did not perform missing mutations; normal success paths still left generic state pending; terminal-state repair, full fault testing, security evidence, hosted artifacts, and review-thread closure remained incomplete. This PR closes the reconciliation runtime.

> PR #134 added typed results, limited renewal, manual membership creation and partial plan wiring, but proposal, exclusion, dependency and lifecycle handlers still did not apply missing projection steps; synchronous workflows left generic state incomplete; terminal replay/history contained P1 defects; production idempotency repair and hosted Elasticsearch evidence remained absent. This PR closes those blockers.

> PR #131 implemented Elasticsearch operation-state and immutable-history persistence primitives only. This PR wires every scoped mutation to those primitives, implements operation-specific repair handlers, and certifies crash recovery and stale-worker fencing against Elasticsearch 9.4.2.

> PR #132 introduced generic reconciliation envelopes and dispatch scaffolding, but all operation kinds still used one non-repairing DurablePlanHandler and mutation services did not create the new operation state. This PR implements concrete projection-aware handlers and wires every scoped mutation into the runtime.

> PR #133 introduced named projection-aware handlers and partial mutation bootstrapping, but missing projection steps still returned retry rather than being repaired; proposal and exclusion workflows were not wired; synchronous paths left generic state incomplete; and real Elasticsearch fault certification remained absent. This PR closes those runtime gaps.

Release readiness remains **blocked**. Hosted artifact cells remain pending until the draft PR workflow produces downloadable evidence; local tests are not represented as hosted certification.

| Capability | PR #140 defect | Required final behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| dependency durable-plan execution | recovery only inspected the projection | apply the scoped detailed plan and verify the complete snapshot | covered | pending | pending | pending |
| dependency token/partial-write recovery | target token caused retry | idempotently apply missing upserts and tombstones | covered | pending | pending | pending |
| lifecycle revision evidence | recovery stopped after projection | finalize the durable event and verify its immutable snapshot | covered | pending | pending | pending |
| proposal pending retry delegation | mutable proposal was validated first | reconcile the reservation operation before mutable validation | covered | pending | pending | pending |
| retry date mapping and due filtering | range queried flattened data using `now` | mapped top-level date and one concrete UTC query instant | covered | pending | pending | pending |
| state/history/plan/result discrimination | mixed shared-index resources | type filters apply before size and stable sort | covered | pending | pending | pending |
| claim renewal and stale-worker fencing | incomplete phase coverage | assert/renew/checkpoint at terminal boundaries | covered | pending | pending | pending |
| hosted manifest and review-thread closure | no retained run | retain real JUnit/scenario/security artifacts before resolution | n/a | pending | pending | pending |

| Capability | Current main defect | Required behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| terminal outcome replay | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| terminal-state repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical applied history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical failed history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical superseded history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| immutable result reuse | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency completed repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency failed repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency superseded repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| pending idempotency operation binding | rejected an unbound reservation | bind `None` only after fingerprint and scope validation | covered | pending | pending | pending |
| full canonical terminal comparison | compared outcome and checksums only | compare every deterministic terminal semantic field | covered | pending | pending | pending |
| handler context usage | handlers received a raw ignored claim | claim assertion, renewal, and phase checkpoint API | covered | pending | pending | pending |
| manual projection repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| manual business terminal repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal accept repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal reject repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal expire repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal supersede repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| membership exclusion repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency product token | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency upserts | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency tombstones | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency complete immutable result | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency >200 upstream result | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency claim renewal | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| lifecycle pre-transition plan/state | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| lifecycle transition repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| synchronous generic result/history/state | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| pending retry delegation | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| authoritative reconciler | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| retry scheduling | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| attempt exhaustion | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| two-worker takeover | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| stale-worker fencing | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| real Elasticsearch matrix | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| real security matrix | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| hosted manifest | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| review threads | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal non-accept result construction | read nonexistent proposal `revision` / `etag` | typed proposal revision/state and canonical result checksum | covered | pending | pending | pending |
| legacy worker identity compatibility | worker delivery id participated in business equality | ignore worker id while preserving immutable legacy event | covered | pending | pending | pending |
| idempotency scope/action/fingerprint binding | repair checked only fingerprint and operation id | OCC bind/verify tenant, environment, product, action, fingerprint, operation | covered | pending | partial | pending |
| dependency >1,000 edge completeness | one bounded page can truncate evidence | verify complete durable snapshot | pending | pending | pending | pending |
| state/history/plan/result discrimination | envelope post-filtering can starve results | discriminate in Elasticsearch before size/limit | partial | pending | pending | pending |
| hosted manifest and review-thread closure | no retained hosted proof | resolve only from successful retained workflow evidence | n/a | pending | pending | pending |
| deterministic proposal result | recovery sampled a new clock value | derive `applied_at` from immutable pending decision evidence | covered | pending | pending | pending |
| proposal terminal revisit decoding | replay assumed generic revision/ETag fields | decode by operation kind and bind non-accept decisions to the result checksum | covered | pending | pending | pending |

| Operation kind | Plan created before mutation? | State created before mutation? | Handler can create missing projection? | Handler can repair terminal evidence? | Handler can repair result/state/idempotency? | Real ES fault matrix | Hosted artifact |
|---|---|---|---|---|---|---|---|
| `manual_membership` | yes | yes | yes | generic only | yes | pending | pending |
| `proposal_accept` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_reject` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_expire` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_supersede` | yes | yes | pending | generic only | yes | pending | pending |
| `membership_exclude` | yes | yes | pending | generic only | yes | pending | pending |
| `dependency_replace` | yes | yes | pending detailed-plan application | generic only | yes | pending | pending |
| `product_lifecycle` | **no** | **no** | pending | generic only | yes | pending | pending |


## Runtime control audit

| Control | Runtime closure |
|---|---|
| operation-state / immutable-history mapping | envelope action and typed document fields distinguish immutable records; OCC metadata is not business state |
| state and history creation | create-or-canonical-verify |
| claim CAS / expiry / renewal | pending or expired claims only; generation and Elasticsearch OCC fencing |
| stale-worker fencing | scope, owner, generation, current OCC metadata, and expiry validated |
| checkpointing | deterministic checkpoint follows handler projection verification |
| terminal history and result persistence | immutable result is written before mutable completion |
| canonical actor / worker policy | actor and reason are durable plan fields and must match; ephemeral worker identity is redacted from canonical terminal history |
| idempotency repair | scope-safe record reference on operation state |
| batch and CLI execution | bounded batch and single-operation commands under `bin/dataobs` |
| two-worker race | loser receives typed retry without handler mutation |
| tenant isolation | deterministic scoped IDs and scope-bound claims/plans/results |
| secret leakage | CLI summary contains identifiers/status only; raw idempotency keys are not persisted |

## Fail-closed gate tracker

| Gate | Status |
|---|---|
| typed plan completeness | partial; manual and proposal targets are complete, dependency/lifecycle remain gated |
| synchronous checkpoints/result/history/state completion | pending coordinator wiring |
| pending retry delegation | pending for mutation entry points |
| claim renewal | implemented at bounded terminal phases; dependency phase renewal pending |
| attempt counting / retry backoff | claimed-generation counting implemented; durable retry scheduling pending |
| stale-worker fencing | repository claim ownership is checked before checkpoint and terminal state writes |
| terminal applied/superseded/failed history | implemented for reconciliation outcomes |
| two-worker recovery / tenant isolation | unit coverage present; full Elasticsearch matrix pending |
| CLI execution / secret leakage | typed redacted output and documented exit codes implemented; hosted proof pending |

The next milestone is Data Product APIs, Product 360, browser/security, and final hosted core certification.

## Evidence status and mapping decision

Migrations `0001`–`0016` remain immutable. The existing generic document mapping is retained until the strict Elasticsearch writer/query suite proves that a `0017` mapping is necessary; no unproven mapping fields are added here. Plan/result persistence, state/history creation, CAS claiming, expiry/takeover, renewal, stale-worker fencing, checkpoints, bounded attempts, two-worker races, tenant isolation, CLI exit behavior, and leakage remain explicit certification controls. Hosted cells above intentionally remain pending until GitHub Actions artifacts exist.

Release readiness remains **blocked**. The next milestone is **Data Product APIs, Product 360, browser/security, and final hosted core certification**.

## Recoverable coordinator implementation gate

The synchronous manual-membership, proposal-decision, membership-exclusion,
dependency-replacement, and lifecycle entry points now create generic durable
state through `RecoverableDataProductOperationCoordinator` and delegate generic
completion to `DataProductOperationService`. Projection success is no longer
considered completion: immutable results and terminal history precede repaired
idempotency and applied state.

Lifecycle plans contain the complete target product and are persisted before
the OCC update; the lifecycle handler can apply that target when the source
revision and ETag still match. Dependency results are read from a complete
snapshot and every planned upsert/tombstone is checksum-verified, avoiding a
single-page result cap. Retryable reconciliation releases its claim into a
persisted, due-time-filtered retry schedule, and non-accept proposal replay uses
the durable UTC `payload.applied_at` rather than envelope persistence time.

This remains an implementation-only gate. Release readiness is **blocked** and
the next gate is **real Elasticsearch 9.4.2 reconciliation, security, and hosted
artifact certification**; no Product 360, Impact, SLO, reliability, coverage,
RCA, or production-readiness capability is promoted here.
# Hosted certification foundation

The pull-request gate uses the explicit `data-product-runtime-foundation`
profile on Elasticsearch 9.4.2. Its retained scenarios prove migration,
mapping, operation-state query, discriminator, baseline persistence isolation,
and positive sentinel redaction infrastructure. The profile promotes no
product capability: `capabilities` remains empty, release readiness remains
`blocked`, and full reconciliation certification is false.

The separate `data-product-reconciliation-full` profile retains the complete
membership, proposal, dependency, lifecycle, takeover, terminal-revisit, CLI,
and security inventory. Foundation evidence cannot satisfy that inventory.
The next certification task is the complete Data Product mutation fault
matrix; Product 360 and the other production-readiness tracks remain out of
scope.
# Hosted foundation truth audit after PR #146

PR #146 created the foundation profile and test-owned evidence plumbing, but several scenarios recorded success without executing the claimed behaviour, the workflow invoked an unsupported migration command, security controls were over-reported, and no pull-request-triggered retained proof existed. This PR makes the foundation evidence semantically true and proves it on Elasticsearch 9.4.2.

| Foundation capability | Current main after PR #146 | Required final behaviour | Unit/contract | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| Migration CLI and clean/upgrade/repeat paths | Unsupported command and pre-migrated inspection | Supported `apply`; destructive clean install; bounded 0016 upgrade; two repeat applies | Migration selection and workflow parser | Dedicated migration module | N/A | migration JSON and JUnit |
| Mapping and retry eligibility | Mapping inspected; GET-only retry evidence | Installed strict mapping and injected, timezone-aware query instant | Query construction/parity | Boundary selection before limit | N/A | mapping/retry JSON |
| Claim expiry and resource discrimination | GET-only evidence | Boundary takeover and mixed-kind filtering before size | Repository contract | Real OCC and shared index | Wrong-scope denial | claim/resource JSON |
| Scoped state, plan, result, history, and search | Controls appended without assertions | One executed owner and positive assertion count per control | Report verifier negatives | Real persistence | Eight required controls | security report/JUnit |
| Sentinel, inventory, JUnit, and provenance | Initial fixture count and broad manifest claims | Final retained scan, exact foundation inventory, no required skips, foundation-only threads/versions | Workflow/evidence contracts | Observed Elasticsearch version | Four sentinel classes | retained manifest and hashes |
| Hosted run, retention, and thread closure | No PR-triggered proof | Successful final-head PR run, downloadable retained evidence, then exact thread replies | N/A | Required | Required | Pending hosted run |

Release readiness remains **blocked**. No product capability is promoted. After this gate, the next task is the complete Data Product mutation fault matrix; this foundation does not claim full reconciliation certification.

## PR #148 foundation-gate truth audit

PR #148 completed most foundation implementation, but its manifest rejected intentional unit-suite skips, its mixed-resource test failed before execution because of a noncanonical result checksum, its stale-worker test could pass because the replacement claim was already expired, and no hosted retained proof existed. This PR closes those blockers and completes the foundation gate.

| Foundation capability | PR #148 state | Correct final behaviour | Local contract | Elasticsearch 9.4.2 | Hosted artifact |
|---|---|---|---|---|---|
| JUnit skip policy by suite | One zero-skip rule | Explicit policy for every owned XML | Exact inventory/policy equality | Real-stack XML requires zero skips | Manifest policy and summaries |
| Unit opt-in skip accounting | Intentional skips rejected | Only two named opt-in reasons, non-empty and bounded | Positive and unknown-reason negatives | N/A | `unit.xml` summary |
| Migration JUnit validation | Retained separately | Non-empty, failure-free, zero skips | Manifest negative | Clean/0016 upgrade/repeat/mapping execute | `migrations.xml` |
| Operation-state JUnit validation | Retained separately | Non-empty, failure-free, zero skips | Manifest negative | Boundary and discriminator scenarios execute | `elasticsearch.xml` |
| Security JUnit validation | Retained | Non-empty, failure-free, zero skips | Manifest negative | Scoped mutation controls execute | `security.xml` |
| Canonical operation-result checksum fixture | Fake `checksum-N` | Checksum is derived from each payload and asserted | Canonical helper contract | Save reaches discrimination assertions | `resource-discriminator.json` |
| Mixed-resource discrimination execution | Failed during result save | State/kind/retry filters precede size; typed reads remain isolated | Seed-count evidence contract | States, plans, results, history, and legacy coexist | Actual seed counts and limit |
| Live worker-B claim | Fixed January 2026 expiry | Expiry is safely beyond wall clock | Expired replacement is not acceptable proof | Positive assert/checkpoint/renew | `claim-expiry-boundaries.json` |
| Stale worker-A owner/generation fencing | Could share expiry failure | All six paths reject stale owner/generation | Named fencing assertions | OCC generation two remains owned by B | Claim scenario assertions |
| Worker-B positive ownership proof | Missing | Assert, checkpoint, renew, and post-stale assert succeed | Named positive assertions | Live expiry/checkpoint re-read | Claim scenario assertions |
| Pull-request workflow | No run | Final-head `pull_request` run; all six jobs succeed | Workflow job contract | Service image is 9.4.2 | Run URL and job conclusions |
| Retained ZIP download | Not done | Download named retained artifact to a clean directory | Exact inventory verifier | N/A | Artifact ID/name/retention |
| Hash and manifest verification | Not independently done | Byte-identical aliases and every artifact hash verified | Fail-closed verifier tests | Version/provenance checked | Manifest SHA-256 |
| Review-thread closure | Hosted proof absent | Resolve only eligible foundation threads after proof | Exact references retained | Test/job evidence cited | Thread replies include run/artifact |

Release readiness remains **blocked**, `full_reconciliation_certified` remains false, and no capability is promoted. The next task remains the complete Data Product mutation fault matrix: manual membership, proposals, exclusions, dependencies, lifecycle, takeover, immutable replay, terminal revisit, CLI, and remaining security.

## Final hosted foundation execution attempt

On 2026-07-23, the final hosted foundation execution was attempted from the
`certify/final-hosted-foundation` branch. This execution environment has no
GitHub credentials or configured Git remote, so it cannot inspect or change the
repository Actions policy, dispatch the diagnostic workflow, push this branch,
or create and keep open the required draft pull request. The hosted foundation
therefore remains pending: no diagnostic or pull-request run, Elasticsearch
9.4.2 result, retained artifact, or independent artifact verification is
claimed by this attempt.

Release readiness remains **blocked**, `full_reconciliation_certified` remains
false, and no product capability is promoted. The mutation fault matrix must
not start until an owner or administrator completes and verifies the final-head
pull-request gate described above.
