def attach_openlineage_impact(asset_id, lineage_edges):
    return [e for e in lineage_edges if e.get("source") == asset_id]
