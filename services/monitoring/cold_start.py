from packages.domain_model.monitor import ColdStartState


def cold_start_state(
    sample_count: int, minimum_samples: int, *, stale: bool = False, reset_required: bool = False
) -> ColdStartState:
    if reset_required:
        return ColdStartState.RESET_REQUIRED
    if stale:
        return ColdStartState.STALE
    if sample_count < max(3, minimum_samples // 2):
        return ColdStartState.COLLECTING
    if sample_count < minimum_samples:
        return ColdStartState.PROVISIONAL
    return ColdStartState.MATURE
