def reconciliation_key(invocation_id, node_unique_id, dataset_identity):
    return "|".join(x or "" for x in (invocation_id, node_unique_id, dataset_identity))
