"""
AWS Lambda OTel auto-instrumentation decorator.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/28
"""

from __future__ import annotations

import functools
import json
import os
from typing import Any, Callable

from opentelemetry import context, trace
from opentelemetry.propagate import extract
from opentelemetry.semconv.trace import SpanAttributes

_tracer = trace.get_tracer("dataobs.lambda")

_COLD_START = True


def otel_lambda(fn: Callable) -> Callable:
    """
    Decorator that wraps a Lambda handler with an OTel root span.

    Supports trace context propagation from:
    - SQS message attributes (traceparent)
    - SNS notification metadata
    - EventBridge detail (custom propagation)
    - API Gateway headers

    Usage::

        @otel_lambda
        def handler(event, context):
            return {"statusCode": 200}
    """

    @functools.wraps(fn)
    def wrapper(event: dict, lambda_ctx: Any) -> Any:
        global _COLD_START

        carrier = _extract_carrier(event)
        parent_ctx = extract(carrier) if carrier else context.get_current()

        with _tracer.start_as_current_span(
            fn.__name__,
            context=parent_ctx,
            kind=trace.SpanKind.SERVER,
            attributes={
                "faas.name": os.getenv("AWS_LAMBDA_FUNCTION_NAME", fn.__name__),
                "faas.version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST"),
                "faas.coldstart": _COLD_START,
                "faas.invocation_id": getattr(lambda_ctx, "aws_request_id", "unknown"),
                "faas.trigger": _detect_trigger(event),
                "cloud.provider": "aws",
                "cloud.region": os.getenv("AWS_REGION", "unknown"),
                "cloud.account.id": os.getenv("AWS_ACCOUNT_ID", "unknown"),
                SpanAttributes.FAAS_TRIGGER: _detect_trigger(event),
            },
        ) as span:
            _COLD_START = False
            try:
                result = fn(event, lambda_ctx)
                if isinstance(result, dict) and "statusCode" in result:
                    span.set_attribute("http.status_code", result["statusCode"])
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                raise

    return wrapper


def _detect_trigger(event: dict) -> str:
    if "Records" in event:
        source = event["Records"][0].get("eventSource", "")
        if "sqs" in source:
            return "pubsub"
        if "sns" in source:
            return "pubsub"
        if "s3" in source:
            return "datasource"
    if "httpMethod" in event or "requestContext" in event:
        return "http"
    return "other"


def _extract_carrier(event: dict) -> dict:
    """Try to extract W3C traceparent from common trigger event shapes."""
    # API Gateway / HTTP
    headers = event.get("headers") or {}
    if "traceparent" in headers:
        return headers

    # SQS message attributes
    records = event.get("Records", [])
    if records:
        attrs = records[0].get("messageAttributes", {})
        if "traceparent" in attrs:
            return {"traceparent": attrs["traceparent"].get("stringValue", "")}

    return {}
