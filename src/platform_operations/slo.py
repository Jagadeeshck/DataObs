"""Deterministic error-budget evaluation; absent evidence never passes."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorBudget:
    window_seconds: int
    good_events: int | None
    total_events: int | None
    achieved_ratio: float | None
    objective: float
    budget_remaining: float | None
    burn_rate: float | None
    data_completeness: float
    evaluation_state: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_error_budget(
    *,
    good_events: int | None,
    total_events: int | None,
    objective: float,
    window_seconds: int,
    data_completeness: float = 1.0
) -> ErrorBudget:
    if good_events is None or total_events is None or total_events <= 0 or data_completeness < 1.0:
        return ErrorBudget(
            window_seconds,
            good_events,
            total_events,
            None,
            objective,
            None,
            None,
            data_completeness,
            "insufficient_data",
        )
    if not (0 <= good_events <= total_events) or not (0 < objective < 1):
        raise ValueError("event counts or objective are outside the contract")
    achieved = good_events / total_events
    allowed_bad = 1.0 - objective
    consumed = (1.0 - achieved) / allowed_bad
    remaining = max(-1.0, 1.0 - consumed)
    state = "exhausted" if remaining <= 0 else "at_risk" if remaining < 0.25 else "healthy"
    return ErrorBudget(
        window_seconds, good_events, total_events, achieved, objective, remaining, consumed, data_completeness, state
    )
