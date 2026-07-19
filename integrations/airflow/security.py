def redact(value):
    return {
        k: ("[REDACTED]" if any(x in k.lower() for x in ("token", "secret", "password")) else v)
        for k, v in value.items()
    }
