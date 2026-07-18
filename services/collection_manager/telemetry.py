def emit_audit(action: str, **fields):
    return {"action": action, **fields}
