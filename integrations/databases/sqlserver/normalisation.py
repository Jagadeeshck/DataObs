def canonical_type(native_type: str) -> str:
    native = native_type.lower()
    if native in {"tinyint", "smallint", "int", "bigint"}:
        return "integer"
    if native == "bit":
        return "boolean"
    if native in {"decimal", "numeric", "money", "smallmoney"}:
        return "decimal"
    if native in {"float", "real"}:
        return "float"
    if native in {"date", "time", "datetime", "datetime2", "smalldatetime", "datetimeoffset"}:
        return native
    if native in {"char", "varchar", "nchar", "nvarchar"}:
        return "string"
    if native in {"text", "ntext"}:
        return "text"
    if native in {"binary", "varbinary", "image", "rowversion", "timestamp"}:
        return "binary"
    if native == "uniqueidentifier":
        return "uuid"
    if native == "xml":
        return "xml"
    if native in {"geography", "geometry"}:
        return "spatial"
    if native == "vector":
        return "vector"
    if native in {"json", "hierarchyid", "sql_variant"}:
        return native
    return "other"
