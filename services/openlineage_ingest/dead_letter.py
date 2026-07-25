import hashlib
import re

SECRET = re.compile(r"(?i)(password|token|secret|authorization)\s*[=:]\s*[^,}\s]+")


def safe_dead_letter(payload, reason, source_id):
    preview = SECRET.sub(r"\1=[REDACTED]", str(payload)[:512])
    return {
        "reason": reason,
        "source": source_id,
        "event_fingerprint": hashlib.sha256(str(payload).encode()).hexdigest(),
        "safe_preview": preview,
        "retry_count": 0,
    }
