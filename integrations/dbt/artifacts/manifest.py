def parse(document):
    metadata = document.get("metadata", {})
    nodes = []
    for unique_id, node in document.get("nodes", {}).items():
        nodes.append(
            {
                "unique_id": unique_id,
                "resource_type": node.get("resource_type"),
                "name": node.get("name"),
                "path": node.get("original_file_path"),
                "dependencies": node.get("depends_on", {}).get("nodes", []),
                "owner": node.get("meta", {}).get("owner"),
                "tags": node.get("tags", []),
            }
        )
    return {"schema": metadata.get("dbt_schema_version"), "project_id": metadata.get("project_id"), "nodes": nodes}
