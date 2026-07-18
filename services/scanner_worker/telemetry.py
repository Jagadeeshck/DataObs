def otel_attributes(task):
    return {
        "dataobs.tenant_id": task.tenant_id,
        "deployment.environment": task.environment,
        "dataobs.integration_id": task.integration_id,
        "dataobs.task_id": task.task_id,
        "dataobs.source_system": task.source_system,
    }
