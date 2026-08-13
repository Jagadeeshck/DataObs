from integrations.database import FixedStatementRegistry, Statement

IDENTITY = "SELECT SYS_CONTEXT('USERENV','DB_NAME') AS database_name, SYS_CONTEXT('USERENV','SERVICE_NAME') AS service_name, SYS_CONTEXT('USERENV','CON_NAME') AS container_name, version AS product_version FROM PRODUCT_COMPONENT_VERSION WHERE product LIKE 'Oracle Database%' FETCH FIRST 1 ROW ONLY"
SCHEMAS = "SELECT owner AS schema FROM (SELECT owner FROM ALL_TABLES UNION SELECT owner FROM ALL_VIEWS UNION SELECT owner FROM ALL_MVIEWS) ORDER BY owner"
TABLES = "SELECT owner AS schema,table_name AS table,'TABLE' AS object_type,partitioned,temporary,iot_type,compression,compress_for,row_movement,num_rows AS approximate_rows,'estimated' AS row_count_kind,last_analyzed,external FROM ALL_TABLES ORDER BY owner,table_name"
VIEWS = "SELECT owner AS schema,view_name AS table,'VIEW' AS object_type FROM ALL_VIEWS ORDER BY owner,view_name"
MVIEWS = "SELECT owner AS schema,mview_name AS table,'MATERIALIZED_VIEW' AS object_type,refresh_mode,refresh_method,build_mode,fast_refreshable FROM ALL_MVIEWS ORDER BY owner,mview_name"
COLUMNS = "SELECT owner AS schema,table_name AS table,column_name AS column,column_id AS ordinal,data_type AS native_type,data_length,data_precision,data_scale,nullable,char_used,char_length,identity_column,virtual_column,CASE WHEN data_type='VECTOR' THEN 1 ELSE 0 END AS is_vector FROM ALL_TAB_COLUMNS ORDER BY owner,table_name,column_id"
VECTOR_COLUMNS = "SELECT owner AS schema,table_name AS table,column_name AS column,column_id AS ordinal,data_type AS native_type,data_length,data_precision,data_scale,nullable,char_used,char_length,identity_column,virtual_column,CASE WHEN data_type='VECTOR' THEN 1 ELSE 0 END AS is_vector,vector_dimension AS vector_dimensions,vector_info AS vector_element_type FROM ALL_TAB_COLUMNS ORDER BY owner,table_name,column_id"
CONSTRAINTS = "SELECT c.owner AS schema,c.table_name AS table,c.constraint_name,c.constraint_type,cc.position AS ordinal,cc.column_name AS column,c.r_owner AS referenced_owner,rc.table_name AS referenced_table,rcc.column_name AS referenced_column,c.delete_rule,c.status,c.validated,c.deferrable,c.deferred,CASE WHEN c.constraint_type='C' THEN 1 ELSE 0 END AS check_constraint_present FROM ALL_CONSTRAINTS c LEFT JOIN ALL_CONS_COLUMNS cc ON cc.owner=c.owner AND cc.constraint_name=c.constraint_name LEFT JOIN ALL_CONSTRAINTS rc ON rc.owner=c.r_owner AND rc.constraint_name=c.r_constraint_name LEFT JOIN ALL_CONS_COLUMNS rcc ON rcc.owner=rc.owner AND rcc.constraint_name=rc.constraint_name AND rcc.position=cc.position WHERE c.constraint_type IN ('P','U','R','C') ORDER BY c.owner,c.table_name,c.constraint_name,cc.position"
INDEXES = "SELECT i.owner AS schema,i.table_name AS table,i.index_name,i.index_type,i.uniqueness,i.partitioned,i.status,i.visibility,i.auto,i.domidx_status,ic.column_position AS ordinal,ic.column_name AS column,ic.descend FROM ALL_INDEXES i LEFT JOIN ALL_IND_COLUMNS ic ON ic.index_owner=i.owner AND ic.index_name=i.index_name ORDER BY i.owner,i.table_name,i.index_name,ic.column_position"
PARTITIONS = "SELECT p.owner AS schema,p.table_name AS table,p.partitioning_type,p.subpartitioning_type,p.partition_count,tp.partition_name,tp.partition_position AS ordinal,tp.compression,tp.compress_for,tp.num_rows AS approximate_rows,'estimated' AS row_count_kind FROM ALL_PART_TABLES p LEFT JOIN ALL_TAB_PARTITIONS tp ON tp.table_owner=p.owner AND tp.table_name=p.table_name ORDER BY p.owner,p.table_name,tp.partition_position"
REGISTRY = FixedStatementRegistry(
    (
        Statement("identity", IDENTITY, 1),
        Statement("schemas", SCHEMAS, 10000),
        Statement("tables", TABLES, 1000000),
        Statement("views", VIEWS, 1000000),
        Statement("materialized_views", MVIEWS, 1000000),
        Statement("columns", COLUMNS, 5000000),
        Statement("vector_columns", VECTOR_COLUMNS, 5000000),
        Statement("constraints", CONSTRAINTS, 5000000),
        Statement("indexes", INDEXES, 2000000),
        Statement("partitions", PARTITIONS, 2000000),
    )
)
