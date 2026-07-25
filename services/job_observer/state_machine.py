from packages.domain_model.job_run import RunState

TERMINAL = {RunState.SUCCESS, RunState.FAILED, RunState.CANCELLED, RunState.ABORTED, RunState.TIMED_OUT}


def transition(current, incoming, *, correction=False):
    current = RunState(current)
    incoming = RunState(incoming)
    if current in TERMINAL and incoming not in TERMINAL:
        return current
    if current in TERMINAL and incoming in TERMINAL and current != incoming and not correction:
        return current
    return incoming
