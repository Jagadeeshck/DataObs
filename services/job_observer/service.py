import hashlib


def canonical_job_id(tenant, environment, platform, namespace, name):
    value = "\0".join([tenant, environment, platform, namespace, name])
    return "job_" + hashlib.sha256(value.encode()).hexdigest()[:32]


def canonical_run_id(tenant, environment, integration, source_run_id):
    return (
        "run_" + hashlib.sha256("\0".join([tenant, environment, integration, source_run_id]).encode()).hexdigest()[:32]
    )
