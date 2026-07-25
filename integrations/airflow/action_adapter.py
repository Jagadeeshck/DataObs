def build_trigger(config, dag_id, parameters):
    if dag_id not in config.allowed_dags:
        raise PermissionError("DAG is not allowlisted")
    unknown = set(parameters) - config.allowed_config_keys
    if unknown:
        raise ValueError("DAG configuration key is not allowlisted")
    return {"method": "POST", "path": f"/api/v2/dags/{dag_id}/dagRuns", "json": {"conf": parameters}}
