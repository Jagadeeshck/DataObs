from .common import observation, pages


def collect(client, context, cfg, account, region):
    for name in pages(
        client, "list_environments", "Environments", token="NextToken", output_token="NextToken", MaxResults=25
    ):
        item = client.get_environment(Name=name).get("Environment", {})
        logging = item.get("LoggingConfiguration", {})
        safe = {
            "status": item.get("Status"),
            "airflow_version": item.get("AirflowVersion"),
            "environment_class": item.get("EnvironmentClass"),
            "minimum_workers": item.get("MinWorkers"),
            "maximum_workers": item.get("MaxWorkers"),
            "scheduler_count": item.get("Schedulers"),
            "webserver_access_mode": item.get("WebserverAccessMode"),
            "logging_categories_enabled": {
                k: bool(v.get("Enabled")) for k, v in logging.items() if isinstance(v, dict)
            },
            "maintenance_window": item.get("WeeklyMaintenanceWindowStart"),
            "creation_timestamp": item.get("CreatedAt"),
            "last_update_timestamp": item.get("LastUpdate", {}).get("CreatedAt"),
            "network_configured": bool(item.get("NetworkConfiguration")),
            "encryption_configured": bool(item.get("KmsKey")),
        }
        arn = item.get("Arn") or name
        try:
            tags = client.list_tags(ResourceArn=arn).get("Tags", {})
        except Exception:
            tags = {}
        # Intentionally no Airflow REST API, URL, configuration, role or network identifiers.
        yield observation(context, cfg, account, region, "mwaa", "environment", arn, name, safe, tags)
