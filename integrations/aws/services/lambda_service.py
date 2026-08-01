from __future__ import annotations

import fnmatch

from .common import observation, pages


def collect(client, context, cfg, account, region):
    patterns = (cfg.raw.get("service_options") or {}).get("lambda", {}).get("include_function_patterns", ())
    for summary in pages(client, "list_functions", "Functions", token="Marker", output_token="NextMarker", MaxItems=50):
        name = summary.get("FunctionName")
        if patterns and not any(fnmatch.fnmatchcase(name or "", pattern) for pattern in patterns):
            continue
        # get_function_configuration contains Environment; use an explicit field allowlist.
        detail = (
            client.get_function_configuration(FunctionName=name)
            if hasattr(client, "get_function_configuration")
            else summary
        )
        arn = detail.get("FunctionArn") or summary.get("FunctionArn") or name
        safe = {
            "runtime": detail.get("Runtime"),
            "package_type": detail.get("PackageType"),
            "architectures": tuple(detail.get("Architectures", ())),
            "memory_size": detail.get("MemorySize"),
            "timeout": detail.get("Timeout"),
            "last_modified": detail.get("LastModified"),
            "state": detail.get("State"),
            "state_reason_code": detail.get("StateReasonCode"),
            "last_update_status": detail.get("LastUpdateStatus"),
            "ephemeral_storage_size": detail.get("EphemeralStorage", {}).get("Size"),
            "dead_letter_queue_configured": bool(detail.get("DeadLetterConfig", {}).get("TargetArn")),
            "tracing_mode": detail.get("TracingConfig", {}).get("Mode"),
            "vpc_configured": bool(detail.get("VpcConfig", {}).get("VpcId")),
            "layers_count": len(detail.get("Layers", ())),
            "code_signing_configured": bool(detail.get("CodeSigningConfigArn")),
        }
        try:
            concurrency = client.get_function_concurrency(FunctionName=name)
            safe["reserved_concurrency_configured"] = "ReservedConcurrentExecutions" in concurrency
        except Exception:
            safe["reserved_concurrency_configured"] = None
        try:
            tags = client.list_tags(Resource=arn).get("Tags", {})
        except Exception:
            tags = {}
        yield observation(context, cfg, account, region, "lambda", "function", arn, name, safe, tags)
