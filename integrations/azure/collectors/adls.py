from datetime import datetime, timezone

from ..normalisation import observation, resource_id, safe, value
from ..pagination import bounded


def collect(client, context, cfg, item):
    rg, name = item["resource_group"], item["storage_account"]
    raw = client.invoke("storage_account_get", rg, name)
    aid = resource_id(cfg, rg, "microsoft.storage", "storageaccounts", name)
    region = value(raw, "location", "global")
    yield observation(
        context,
        cfg,
        region,
        "adls_gen2",
        "adls.account",
        aid,
        name,
        {
            "resource_group": rg,
            "storage_account": name,
            **safe(
                raw,
                ("kind", "enable_https_traffic_only", "minimum_tls_version", "public_network_access", "is_hns_enabled"),
            ),
            "sku_category": value(value(raw, "sku", {}), "name"),
        },
    )
    if item.get("include_filesystems", True):
        for fs in bounded(
            client.invoke("filesystem_list", name),
            cfg.limits["maximum_pages"],
            cfg.limits["maximum_observations"],
            lambda x: value(x, "name"),
            context,
        ):
            fname = value(fs, "name")
            yield observation(
                context,
                cfg,
                region,
                "adls_gen2",
                "adls.filesystem",
                aid + "/filesystems/" + fname,
                fname,
                {
                    "account_canonical_id": aid,
                    "filesystem_name": fname,
                    "last_modified": value(fs, "last_modified"),
                    "metadata_present": bool(value(fs, "metadata")),
                    "lease_state": value(fs, "lease_state"),
                },
            )
    po = item["prefix_observations"]
    if po["enabled"]:
        for prefix in po["prefixes"]:
            files = dirs = total = 0
            oldest = newest = None
            truncated = False
            try:
                paths = bounded(
                    client.invoke("path_list", name, prefix["filesystem"], prefix["path"]),
                    cfg.limits["maximum_pages"],
                    po["maximum_paths_per_prefix"],
                    lambda x: value(x, "name"),
                    context,
                )
                for p in paths:
                    modified = value(p, "last_modified")
                    is_dir = bool(value(p, "is_directory"))
                    dirs += int(is_dir)
                    files += int(not is_dir)
                    total += 0 if is_dir else int(value(p, "content_length", 0) or 0)
                    if modified:
                        oldest = modified if oldest is None or modified < oldest else oldest
                        newest = modified if newest is None or modified > newest else newest
            except Exception as exc:
                if getattr(exc, "code", None) == "result_truncated":
                    truncated = True
                else:
                    raise
            native = aid + "/filesystems/" + prefix["filesystem"] + "/prefix/" + prefix["path"]
            yield observation(
                context,
                cfg,
                region,
                "adls_gen2",
                "adls.prefix_observation",
                native,
                prefix["filesystem"],
                {
                    "prefix_canonical_id": native,
                    "file_count_observed": None if truncated else files,
                    "directory_count_observed": None if truncated else dirs,
                    "total_content_length": None if truncated else total,
                    "newest_last_modified": newest,
                    "oldest_last_modified": oldest,
                    "scan_completeness": "partial" if truncated else "complete",
                    "truncated": truncated,
                    "freshness_method": "adls_prefix_max_last_modified",
                    "path_names_emitted": False,
                },
            )
