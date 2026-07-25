TERMINAL = {"COMPLETE", "FAIL", "ABORT", "OTHER"}
PRECEDENCE = {"START": 1, "RUNNING": 2, "COMPLETE": 3, "FAIL": 3, "ABORT": 3, "OTHER": 3}


def resolve(current, incoming):
    if current is None:
        return incoming
    cs, ct = current
    ns, nt = incoming
    if PRECEDENCE.get(ns, 0) > PRECEDENCE.get(cs, 0):
        return incoming
    if PRECEDENCE.get(ns, 0) < PRECEDENCE.get(cs, 0):
        return current
    # A newer terminal wins; equal timestamps are stable by lexical state.
    return incoming if (nt, ns) > (ct, cs) else current
