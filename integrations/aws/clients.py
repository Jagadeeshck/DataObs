from __future__ import annotations

import os
from typing import Any, Callable

from .errors import map_aws_error


class AwsClientFactory:
    def __init__(self, configuration, session_factory: Callable[..., Any] | None = None):
        if session_factory is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise RuntimeError("boto3 dependency is required") from exc
            self._sdk_config = Config(
                connect_timeout=5, read_timeout=20, retries={"max_attempts": 4, "mode": "standard"}
            )
            session_factory = boto3.Session
        else:
            self._sdk_config = None
        self.configuration, self.session_factory, self._clients = configuration, session_factory, {}
        self.session = session_factory()
        role = configuration.raw.get("assume_role") or {}
        if role:
            kwargs = {
                "RoleArn": role["role_arn"],
                "RoleSessionName": "dataobs-collector",
                "DurationSeconds": int(role.get("session_duration_seconds", 3600)),
            }
            ref = role.get("external_id_ref")
            if ref:
                if not str(ref).startswith("env:"):
                    raise ValueError("external_id_ref must use env:")
                value = os.environ.get(str(ref)[4:])
                if not value:
                    raise ValueError("external ID reference is unresolved")
                kwargs["ExternalId"] = value
            try:
                credentials = self.session.client("sts", config=self._sdk_config).assume_role(**kwargs)["Credentials"]
            except Exception as exc:
                raise map_aws_error(exc) from exc
            self.session = session_factory(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )

    def client(self, account: str, region: str, service: str):
        key = (account, region, service)
        if key not in self._clients:
            self._clients[key] = self.session.client(
                service,
                region_name=region,
                config=self._sdk_config,
                **(
                    {"endpoint_url": self.configuration.raw["sts_endpoint_url"]}
                    if service == "sts" and self.configuration.raw.get("sts_endpoint_url")
                    else {}
                ),
            )
        return self._clients[key]
