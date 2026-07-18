from packages.domain_model.identity import deterministic_id


def task_id_for(policy_id: str, scanner_id: str) -> str:
    return deterministic_id("task", [policy_id, scanner_id])
