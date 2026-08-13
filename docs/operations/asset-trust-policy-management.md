# Asset trust policy management

Policies are bounded declarative data: weights must use the eight known dimensions, be finite/non-negative, and
sum to one. Updates require actor/reason at the API boundary, `If-Match`, and an exactly incremented revision.
Stale ETags fail rather than overwrite. Historical evaluations retain their policy ID and version. Roll back by
disabling the new revision and selecting a prior/new corrective policy for future evaluations; never rewrite history.
