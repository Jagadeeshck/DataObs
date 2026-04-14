# DataObs — dbt Integration

Surface dbt model run results and test outcomes as OTel spans.

## Options

### Option A — dbt Core (parse run_results.json)
```bash
dbt run --profiles-dir . && \
python -c "
from parse_run_results import parse_and_emit
parse_and_emit('target/run_results.json')
"
```

### Option B — dbt Cloud Poller
```bash
DBT_CLOUD_ACCOUNT_ID=123 DBT_CLOUD_API_TOKEN=xxx \
python -c "
from dbt_cloud_poller import DbtCloudPoller
DbtCloudPoller(account_id='123', api_token='xxx').run_forever()
"
```

## Semconv Mapping

| dbt concept | OTel attribute |
|-------------|---------------|
| model name | `db.sql.table` |
| adapter type | `db.system` |
| run status | `dbt.status` |
| rows affected | `dbt.rows_affected` |

Resolves: [#29](https://github.com/Jagadeeshck/DataObs/issues/29)
