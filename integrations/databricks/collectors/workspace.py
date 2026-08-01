from __future__ import annotations

from ..normalisation import fingerprint, observation


def collect(client, context, cfg, sdk_version):
    identity = client.workspace.get_status()
    workspace_id = str(identity.get("workspace_id") if isinstance(identity, dict) else identity.workspace_id)
    if workspace_id != cfg.expected_workspace_id:
        from ..errors import safe_error

        raise safe_error("workspace_mismatch")
    return observation(
        context,
        workspace_id,
        cfg.cloud,
        "workspace",
        workspace_id,
        "Databricks workspace",
        {
            "provider_type": "databricks",
            "provider_version": "1",
            "cloud": cfg.cloud,
            "workspace_id": workspace_id,
            "workspace_host_fingerprint": fingerprint(cfg.workspace_host),
            "sdk_version": sdk_version,
        },
    )
