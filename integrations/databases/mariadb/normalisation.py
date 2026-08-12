def canonical_type(native_type: str, column_type: str = "") -> str:
    native = native_type.lower()
    detail = column_type.lower()
    if native == "tinyint" and detail.startswith("tinyint(1)"):
        return "boolean"
    if native in {"tinyint", "smallint", "mediumint", "int", "integer", "bigint", "bit"}:
        return "unsigned_integer" if "unsigned" in detail else "integer"
    if native in {"decimal", "numeric"}:
        return "decimal"
    if native in {"float", "double", "real"}:
        return "float"
    if native in {"char", "varchar"}:
        return "string"
    if native.endswith("text"):
        return "text"
    if native.endswith("blob"):
        return "blob"
    if native in {"binary", "varbinary"}:
        return "binary"
    if native in {"date", "datetime", "timestamp", "time", "year"}:
        return native
    # MariaDB JSON is a LONGTEXT alias, while UUID and INET types are native.
    if native in {"json", "uuid", "inet4", "inet6"}:
        return native
    if native in {"enum", "set"}:
        return native
    if native in {
        "geometry",
        "point",
        "linestring",
        "polygon",
        "multipoint",
        "multilinestring",
        "multipolygon",
        "geometrycollection",
    }:
        return "spatial"
    if native == "vector":
        return "vector"
    return "other"


def storage_engine(value):
    return value if value in {"InnoDB", "Aria", "MyISAM", "MEMORY", "ColumnStore", "MyRocks"} else "other"
