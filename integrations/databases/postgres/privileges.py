LEAST_PRIVILEGE_SQL = """
CREATE ROLE dataobs_metadata LOGIN PASSWORD '<managed outside DataObs>';
GRANT CONNECT ON DATABASE mydb TO dataobs_metadata;
GRANT USAGE ON SCHEMA public TO dataobs_metadata;
GRANT SELECT ON pg_catalog.pg_class, pg_catalog.pg_namespace, pg_catalog.pg_attribute TO dataobs_metadata;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dataobs_metadata; -- only required for opt-in aggregate profiling/freshness
"""
