from integrations.database import FixedStatementRegistry, Statement

SCHEMAS = "SELECT SCHEMA_NAME AS `schema`, DEFAULT_CHARACTER_SET_NAME AS default_character_set, DEFAULT_COLLATION_NAME AS default_collation FROM information_schema.schemata ORDER BY SCHEMA_NAME"
RELATIONS = "SELECT TABLE_SCHEMA AS `schema`, TABLE_NAME AS `table`, TABLE_TYPE AS table_type, ENGINE AS engine, TABLE_ROWS AS approximate_rows, DATA_LENGTH AS data_bytes, INDEX_LENGTH AS index_bytes, TABLE_COLLATION AS collation, CREATE_TIME AS create_time, UPDATE_TIME AS update_time FROM information_schema.tables ORDER BY TABLE_SCHEMA,TABLE_NAME"
COLUMNS = "SELECT TABLE_SCHEMA AS `schema`, TABLE_NAME AS `table`, COLUMN_NAME AS `column`, ORDINAL_POSITION AS ordinal, DATA_TYPE AS native_type, COLUMN_TYPE AS column_type, IS_NULLABLE AS nullable, NUMERIC_PRECISION AS numeric_precision, NUMERIC_SCALE AS numeric_scale, CHARACTER_MAXIMUM_LENGTH AS character_length, DATETIME_PRECISION AS datetime_precision, EXTRA AS extra FROM information_schema.columns ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION"
CONSTRAINTS = "SELECT tc.TABLE_SCHEMA AS `schema`,tc.TABLE_NAME AS `table`,tc.CONSTRAINT_NAME AS constraint_name,tc.CONSTRAINT_TYPE AS constraint_type,kcu.COLUMN_NAME AS `column`,kcu.ORDINAL_POSITION AS ordinal,kcu.REFERENCED_TABLE_SCHEMA AS referenced_schema,kcu.REFERENCED_TABLE_NAME AS referenced_table,kcu.REFERENCED_COLUMN_NAME AS referenced_column,rc.UPDATE_RULE AS update_rule,rc.DELETE_RULE AS delete_rule,(cc.CONSTRAINT_NAME IS NOT NULL) AS check_constraint_present FROM information_schema.table_constraints tc LEFT JOIN information_schema.key_column_usage kcu ON kcu.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND kcu.CONSTRAINT_NAME=tc.CONSTRAINT_NAME AND kcu.TABLE_NAME=tc.TABLE_NAME LEFT JOIN information_schema.referential_constraints rc ON rc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND rc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME LEFT JOIN information_schema.check_constraints cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME ORDER BY tc.TABLE_SCHEMA,tc.TABLE_NAME,tc.CONSTRAINT_NAME,kcu.ORDINAL_POSITION"
INDEXES = "SELECT TABLE_SCHEMA AS `schema`,TABLE_NAME AS `table`,INDEX_NAME AS index_name,NON_UNIQUE AS non_unique,INDEX_TYPE AS index_type,SEQ_IN_INDEX AS sequence,COLUMN_NAME AS `column`,CARDINALITY AS cardinality,IGNORED AS ignored,(COLUMN_NAME IS NULL) AS functional_index FROM information_schema.statistics ORDER BY TABLE_SCHEMA,TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX"
PARTITIONS = "SELECT TABLE_SCHEMA AS `schema`,TABLE_NAME AS `table`,PARTITION_NAME AS partition_name,SUBPARTITION_NAME AS subpartition_name,PARTITION_ORDINAL_POSITION AS partition_ordinal,SUBPARTITION_ORDINAL_POSITION AS subpartition_ordinal,PARTITION_METHOD AS partition_method,SUBPARTITION_METHOD AS subpartition_method,TABLE_ROWS AS approximate_rows FROM information_schema.partitions WHERE PARTITION_NAME IS NOT NULL ORDER BY TABLE_SCHEMA,TABLE_NAME,PARTITION_ORDINAL_POSITION,SUBPARTITION_ORDINAL_POSITION"
REGISTRY = FixedStatementRegistry(
    (
        Statement("health", "SELECT VERSION() AS server_version, @@version_comment AS version_comment", 1),
        Statement("schemas", SCHEMAS, 10000),
        Statement("relations", RELATIONS, 1000000),
        Statement("columns", COLUMNS, 5000000),
        Statement("constraints", CONSTRAINTS, 5000000),
        Statement("indexes", INDEXES, 2000000),
        Statement("partitions", PARTITIONS, 2000000),
    )
)
