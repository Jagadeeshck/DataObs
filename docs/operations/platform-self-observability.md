# Platform self-observability

The canonical backend runtime is `src/telemetry.py`; export is opt-in, bounded, TLS-oriented and fail-open. Metric dimensions are centrally allowlisted. The API and packaged workers use stable component/operation names. Exporter state is optional: loss of telemetry may degrade operator visibility but must not fail product traffic. Current implementation is locally testable; hosted exact-SHA capture and operational certification remain pending.
