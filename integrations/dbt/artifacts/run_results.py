import hashlib


def parse(document):
    out = []
    for result in document.get("results", []):
        # Keep only a one-way fingerprint; never return compiled/raw SQL.
        code = result.get("compiled_code") or result.get("compiled_sql")
        out.append(
            {
                "unique_id": result.get("unique_id"),
                "status": result.get("status"),
                "timing": result.get("timing", []),
                "thread_id": result.get("thread_id"),
                "adapter_response": result.get("adapter_response", {}),
                "compiled_code_fingerprint": hashlib.sha256(code.encode()).hexdigest() if code else None,
            }
        )
    return {"invocation_id": document.get("metadata", {}).get("invocation_id"), "results": out}
