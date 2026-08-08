from __future__ import annotations

WIDENING = {
    "integer": {"long", "float", "double", "decimal"},
    "long": {"float", "double", "decimal"},
    "float": {"double", "decimal"},
}


def type_compatibility(expected: str | None, observed: str | None, allowed: tuple[str, ...] = ()) -> str:
    if not expected or not observed:
        return "unknown"
    expected, observed = expected.lower(), observed.lower()
    if expected == observed or observed in {x.lower() for x in allowed}:
        return "compatible"
    if observed in WIDENING.get(expected, set()):
        return "widening"
    if expected in WIDENING.get(observed, set()):
        return "narrowing"
    return "incompatible"
