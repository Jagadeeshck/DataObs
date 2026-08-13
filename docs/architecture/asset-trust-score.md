# Asset Trust and Reliability Score v1

Asset Trust is an asset-level, deterministic aggregation of canonical evidence. It answers what observed
reliability evidence indicates; it is not a guarantee of correctness, a Business Risk Score, or a replacement
for Data Product Reliability.

The eight dimensions and default weights are quality (20%), freshness (15%), delivery reliability (15%), SLO
reliability (20%), contract compliance (10%), schema stability (5%), observability coverage (10%), and lineage
and governance (5%). For observed dimensions, `uncapped = sum(score × weight) / available weight`. Missing
dimensions are excluded from this numerical result rather than treated as zero.

Coverage is `sum(weight × source coverage)`. Confidence is `coverage × freshness factor × source confidence
factor`. Required evidence gaps or confidence below 0.60 yield `partial`; no eligible evidence yields `unknown`.
Policy-driven, high-confidence severe evidence may cap the result. v1 defaults are critical contract violation
at 60, exhausted SLO budget at 65, and critical freshness breach at 50. Responses retain the uncapped score,
cap reason, weights, available weight, confidence, coverage, and evidence references.

Criticality and downstream impact prioritize investigation but never alter trust. Data Products may show member
asset trust context while their existing reliability score remains independent.
