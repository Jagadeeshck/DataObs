# Schema change classification

Schema fingerprints canonicalize ordered column definitions and partition fields; version and change IDs are deterministic. Nullable additions are additive, drops and partition changes are breaking, nullability tightening and known narrowing are potentially breaking, and known widening is compatible. Unknown provider-specific conversions remain unknown. Constraint changes are potentially breaking. A matching removed/added shape is only an inferred rename candidate unless provider evidence proves a rename. Every result carries the selected rule reason codes.
