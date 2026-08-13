def canonical_type(native_type: str) -> str:
    value = " ".join(native_type.upper().split())
    if value in {"NUMBER"}:
        return "decimal"
    if value in {"FLOAT", "BINARY_FLOAT", "BINARY_DOUBLE"}:
        return "float"
    if value in {"CHAR", "VARCHAR2", "NCHAR", "NVARCHAR2"}:
        return "string"
    if value in {"CLOB", "NCLOB", "LONG"}:
        return "text"
    if value in {"BLOB", "RAW", "LONG RAW"}:
        return "binary"
    if value == "DATE" or value.startswith("TIMESTAMP"):
        return value.lower().replace(" ", "_")
    if value.startswith("INTERVAL"):
        return "interval"
    if value in {"ROWID", "UROWID"}:
        return "rowid"
    if value == "XMLTYPE":
        return "xml"
    if value == "JSON":
        return "json"
    if value == "BOOLEAN":
        return "boolean"
    if value == "VECTOR":
        return "vector"
    return "other"
