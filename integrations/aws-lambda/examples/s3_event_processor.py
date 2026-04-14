"""
S3 event-driven Lambda — instrumented with @otel_lambda.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/28
"""
from __future__ import annotations

from opentelemetry import trace
from otel_lambda import otel_lambda

tracer = trace.get_tracer("dataobs.lambda.s3-processor")


@otel_lambda
def handler(event: dict, context: object) -> dict:
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        with tracer.start_as_current_span(
            "s3.process_object",
            attributes={"s3.bucket": bucket, "s3.key": key},
        ):
            # TODO: implement actual processing
            pass

    return {"statusCode": 200, "body": "OK"}
