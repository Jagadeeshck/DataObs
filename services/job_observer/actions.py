ALLOWED = {"trigger_airflow_dag", "retry_airflow_task", "rerun_dbt_cloud_job", "invoke_spark_runbook"}


def validate_action(action, parameters, allowed_keys):
    if action not in ALLOWED:
        raise ValueError("action is not allowlisted")
    unknown = set(parameters) - set(allowed_keys)
    if unknown:
        raise ValueError(f"parameters are not allowlisted: {sorted(unknown)}")
    return True
