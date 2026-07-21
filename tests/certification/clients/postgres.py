import os
from pathlib import Path


class PostgresClient:
    def connect(self):
        import psycopg

        password = Path(os.environ["CERTIFICATION_POSTGRES_PASSWORD_FILE"]).read_text().strip()
        return psycopg.connect(os.environ["CERTIFICATION_POSTGRES_DSN"], password=password, connect_timeout=10)
