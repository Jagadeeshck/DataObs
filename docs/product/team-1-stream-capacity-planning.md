# Stream capacity planning

Stream 360 presents measured capacity separately from derived recovery capacity, estimated forecasts, and hypothetical scenarios. Operators can review provider-aware, advisory-only recommendations; DataObs never executes scaling, partition, shard, quota, retention, consumer, or broker changes.

A recovery target derives `required processing rate = arrival rate + backlog / target seconds`. This is labelled **Derived**, never measured. Forecasts show ranges, coverage, confidence, missing inputs, and limitations. Unknown limits display **Limit unavailable**, not zero utilisation.

Dependent Data Products are **potentially exposed** when an upstream stream is constrained. This does not assert observed business degradation or causality.
