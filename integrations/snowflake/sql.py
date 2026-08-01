from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping


@dataclass(frozen=True)
class SqlTemplate:
    family: str
    text: str
    historical: bool = False


SQL_TEMPLATES = {
    "account": SqlTemplate(
        "account",
        "SELECT CURRENT_ACCOUNT() AS ACCOUNT_NAME, CURRENT_REGION() AS REGION, CURRENT_ROLE() AS ROLE, CURRENT_ORGANIZATION_NAME() AS ORGANIZATION_NAME LIMIT %(limit)s",
    ),
    "warehouses": SqlTemplate(
        "warehouses",
        "SELECT WAREHOUSE_ID, WAREHOUSE_NAME, STATE, TYPE, SIZE, MIN_CLUSTER_COUNT, MAX_CLUSTER_COUNT, SCALING_POLICY, AUTO_SUSPEND, AUTO_RESUME, RESOURCE_MONITOR, CREATED_ON, UPDATED_ON FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES WHERE DELETED_ON IS NULL ORDER BY WAREHOUSE_ID LIMIT %(limit)s",
    ),
    "resource_monitors": SqlTemplate(
        "resource_monitors",
        "SELECT ID, NAME, CREDIT_QUOTA, FREQUENCY, START_TIME, END_TIME, USED_CREDITS FROM SNOWFLAKE.ACCOUNT_USAGE.RESOURCE_MONITORS WHERE END_TIME IS NULL OR END_TIME >= %(start_time)s ORDER BY ID LIMIT %(limit)s",
        True,
    ),
    "databases": SqlTemplate(
        "catalog",
        "SELECT DATABASE_ID, DATABASE_NAME, CREATED, LAST_ALTERED, RETENTION_TIME FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASES WHERE DELETED IS NULL ORDER BY DATABASE_ID LIMIT %(limit)s",
    ),
    "schemas": SqlTemplate(
        "catalog",
        "SELECT SCHEMA_ID, SCHEMA_NAME, CATALOG_NAME, CREATED, LAST_ALTERED, RETENTION_TIME FROM SNOWFLAKE.ACCOUNT_USAGE.SCHEMATA WHERE DELETED IS NULL ORDER BY SCHEMA_ID LIMIT %(limit)s",
    ),
    "tables": SqlTemplate(
        "catalog",
        "SELECT TABLE_ID, TABLE_NAME, TABLE_SCHEMA, TABLE_CATALOG, TABLE_TYPE, IS_TRANSIENT, ROW_COUNT, BYTES, RETENTION_TIME, CREATED, LAST_ALTERED FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES WHERE DELETED IS NULL ORDER BY TABLE_ID LIMIT %(limit)s",
    ),
    "columns": SqlTemplate(
        "catalog",
        "SELECT TABLE_ID, TABLE_NAME, TABLE_SCHEMA, TABLE_CATALOG, COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, IS_NULLABLE, IFF(COLUMN_DEFAULT IS NULL, FALSE, TRUE) AS DEFAULT_PRESENT, IS_IDENTITY, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION FROM SNOWFLAKE.ACCOUNT_USAGE.COLUMNS WHERE DELETED IS NULL ORDER BY TABLE_ID, ORDINAL_POSITION LIMIT %(limit)s",
    ),
    "query_history": SqlTemplate(
        "query_history",
        "SELECT QUERY_ID, QUERY_TYPE, EXECUTION_STATUS, WAREHOUSE_ID, DATABASE_ID, SCHEMA_ID, START_TIME, END_TIME, TOTAL_ELAPSED_TIME, COMPILATION_TIME, EXECUTION_TIME, QUEUED_PROVISIONING_TIME, QUEUED_REPAIR_TIME, QUEUED_OVERLOAD_TIME, TRANSACTION_BLOCKED_TIME, BYTES_SCANNED, PERCENTAGE_SCANNED_FROM_CACHE, ROWS_PRODUCED, ROWS_INSERTED, ROWS_UPDATED, ROWS_DELETED, PARTITIONS_SCANNED, PARTITIONS_TOTAL, BYTES_SPILLED_TO_LOCAL_STORAGE, BYTES_SPILLED_TO_REMOTE_STORAGE, ERROR_CODE FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE START_TIME >= %(start_time)s AND START_TIME < %(end_time)s AND (START_TIME > %(watermark)s OR (START_TIME = %(watermark)s AND QUERY_ID > %(tie_breaker)s)) ORDER BY START_TIME, QUERY_ID LIMIT %(limit)s",
        True,
    ),
    "warehouse_load": SqlTemplate(
        "warehouse_load",
        "SELECT WAREHOUSE_ID, START_TIME, END_TIME, AVG_RUNNING, AVG_QUEUED_LOAD, AVG_QUEUED_PROVISIONING, AVG_BLOCKED FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY WHERE START_TIME >= %(start_time)s AND START_TIME < %(end_time)s ORDER BY START_TIME, WAREHOUSE_ID LIMIT %(limit)s",
        True,
    ),
    "metering": SqlTemplate(
        "warehouse_metering",
        "SELECT WAREHOUSE_ID, START_TIME, END_TIME, CREDITS_USED, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY WHERE START_TIME >= %(start_time)s AND START_TIME < %(end_time)s ORDER BY START_TIME, WAREHOUSE_ID LIMIT %(limit)s",
        True,
    ),
    "storage": SqlTemplate(
        "table_storage",
        "SELECT TABLE_ID, TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, ACTIVE_BYTES, TIME_TRAVEL_BYTES, FAILSAFE_BYTES, RETAINED_FOR_CLONE_BYTES FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS WHERE TABLE_DROPPED IS NULL ORDER BY TABLE_ID LIMIT %(limit)s",
    ),
}


def execute_bounded(
    connection: Any, template: SqlTemplate, parameters: Mapping[str, Any], *, batch_size: int, cancelled=lambda: False
) -> Iterator[Mapping[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(template.text, dict(parameters))
        names = [str(item[0]).lower() for item in cursor.description]
        while not cancelled():
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(zip(names, row))
    finally:
        cursor.close()
