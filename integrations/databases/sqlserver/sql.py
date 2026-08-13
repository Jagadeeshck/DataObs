from integrations.database import FixedStatementRegistry, Statement

IDENTITY = "SELECT CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(128)) AS product_version, CAST(SERVERPROPERTY('ProductName') AS nvarchar(128)) AS product_name, CAST(SERVERPROPERTY('Edition') AS nvarchar(128)) AS edition, CAST(SERVERPROPERTY('EngineEdition') AS int) AS engine_edition, DB_NAME() AS database_name"
SCHEMAS = (
    "SELECT s.name AS [schema] FROM sys.schemas AS s WHERE s.name NOT IN ('sys','INFORMATION_SCHEMA') ORDER BY s.name"
)
RELATIONS = "SELECT s.name AS [schema],t.name AS [table],'TABLE' AS object_type,t.create_date,t.modify_date AS metadata_change_time,t.temporal_type,t.temporal_type_desc,hs.name AS history_schema,ht.name AS history_table,t.is_memory_optimized,t.durability_desc,t.is_node,t.is_edge,t.ledger_type,t.ledger_type_desc FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id LEFT JOIN sys.tables ht ON ht.object_id=t.history_table_id LEFT JOIN sys.schemas hs ON hs.schema_id=ht.schema_id UNION ALL SELECT s.name,v.name,'VIEW',v.create_date,v.modify_date,0,'NON_TEMPORAL_TABLE',NULL,NULL,0,NULL,0,0,0,NULL FROM sys.views v JOIN sys.schemas s ON s.schema_id=v.schema_id ORDER BY [schema],[table]"
COLUMNS_2022 = "SELECT s.name AS [schema],o.name AS [table],c.name AS [column],c.column_id AS ordinal,ty.name AS native_type,c.is_nullable,c.max_length,c.precision,c.scale,c.is_identity,c.is_computed,c.is_sparse,c.is_rowguidcol,c.is_filestream,c.is_hidden,c.is_masked,c.encryption_type_desc FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id WHERE o.type IN ('U','V') ORDER BY s.name,o.name,c.column_id"
COLUMNS_2025 = COLUMNS_2022.replace(
    "c.encryption_type_desc",
    "c.encryption_type_desc,CASE WHEN ty.name='vector' THEN 1 ELSE 0 END AS is_vector,c.vector_dimensions,c.vector_base_type_desc",
)
CONSTRAINTS = "SELECT s.name AS [schema],o.name AS [table],kc.name AS constraint_name,kc.type_desc AS constraint_type,ic.key_ordinal AS ordinal,c.name AS [column],CAST(NULL AS sysname) AS referenced_schema,CAST(NULL AS sysname) AS referenced_table,CAST(NULL AS sysname) AS referenced_column,CAST(NULL AS nvarchar(60)) AS update_action,CAST(NULL AS nvarchar(60)) AS delete_action,CAST(0 AS bit) AS is_disabled,CAST(0 AS bit) AS is_not_trusted FROM sys.key_constraints kc JOIN sys.objects o ON o.object_id=kc.parent_object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.index_columns ic ON ic.object_id=kc.parent_object_id AND ic.index_id=kc.unique_index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id UNION ALL SELECT ss.name,so.name,fk.name,'FOREIGN_KEY_CONSTRAINT',fkc.constraint_column_id,sc.name,ts.name,tobj.name,tc.name,fk.update_referential_action_desc,fk.delete_referential_action_desc,fk.is_disabled,fk.is_not_trusted FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id JOIN sys.objects so ON so.object_id=fk.parent_object_id JOIN sys.schemas ss ON ss.schema_id=so.schema_id JOIN sys.columns sc ON sc.object_id=so.object_id AND sc.column_id=fkc.parent_column_id JOIN sys.objects tobj ON tobj.object_id=fk.referenced_object_id JOIN sys.schemas ts ON ts.schema_id=tobj.schema_id JOIN sys.columns tc ON tc.object_id=tobj.object_id AND tc.column_id=fkc.referenced_column_id UNION ALL SELECT s.name,o.name,x.name,x.type_desc,NULL,NULL,NULL,NULL,NULL,NULL,NULL,x.is_disabled,x.is_not_trusted FROM sys.check_constraints x JOIN sys.objects o ON o.object_id=x.parent_object_id JOIN sys.schemas s ON s.schema_id=o.schema_id UNION ALL SELECT s.name,o.name,x.name,x.type_desc,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,0 FROM sys.default_constraints x JOIN sys.objects o ON o.object_id=x.parent_object_id JOIN sys.schemas s ON s.schema_id=o.schema_id"
INDEXES = "SELECT s.name AS [schema],o.name AS [table],i.name AS index_name,i.type_desc AS index_type,i.is_unique,i.is_primary_key,i.is_unique_constraint,i.is_disabled,i.is_hypothetical,i.has_filter,ic.key_ordinal,ic.index_column_id,ic.is_descending_key,ic.is_included_column,c.name AS [column] FROM sys.indexes i JOIN sys.objects o ON o.object_id=i.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id LEFT JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE o.type='U' ORDER BY s.name,o.name,i.index_id,ic.index_column_id"
PARTITIONS = "SELECT s.name AS [schema],o.name AS [table],i.name AS index_name,p.partition_number,p.rows AS approximate_rows,p.data_compression_desc,COUNT(*) OVER (PARTITION BY p.object_id,p.index_id) AS partition_count,'estimated' AS row_count_kind FROM sys.partitions p JOIN sys.objects o ON o.object_id=p.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.indexes i ON i.object_id=p.object_id AND i.index_id=p.index_id WHERE o.type='U' ORDER BY s.name,o.name,p.index_id,p.partition_number"
STORAGE = "SELECT s.name AS [schema],o.name AS [table],p.partition_number,p.row_count AS approximate_rows,p.used_page_count,p.reserved_page_count,'estimated' AS row_count_kind FROM sys.dm_db_partition_stats p JOIN sys.objects o ON o.object_id=p.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE o.type='U'"

REGISTRY = FixedStatementRegistry(
    (
        Statement("identity", IDENTITY, 1),
        Statement("schemas", SCHEMAS, 10000),
        Statement("relations", RELATIONS, 1000000),
        Statement("columns_2022", COLUMNS_2022, 5000000),
        Statement("columns_2025", COLUMNS_2025, 5000000),
        Statement("constraints", CONSTRAINTS, 5000000),
        Statement("indexes", INDEXES, 2000000),
        Statement("partitions", PARTITIONS, 2000000),
        Statement("storage_statistics", STORAGE, 2000000),
    )
)
