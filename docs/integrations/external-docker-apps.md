# Connect external Docker Compose apps to the DataObs POC

This guide shows how an application running in a separate Docker Compose project can send telemetry to the DataObs POC Elastic Stack by joining the DataObs Docker network.

## Stable DataObs Docker DNS endpoints

Use these URLs **from containers that are attached to the DataObs POC Docker network**:

| Purpose | URL |
|---|---|
| APM intake | `http://dataobs-poc-elastic-agent:8200` |
| Elasticsearch | `http://dataobs-poc-es01:9200` |
| Kibana | `http://dataobs-poc-kibana:5601` |
| Fleet Server | `http://dataobs-poc-fleet-server:8220` |

The port split is intentional:

- **APM agents use `8200`** to send traces, metrics, and errors to the APM integration hosted by the Fleet-managed Elastic Agent container.
- **Fleet enrolment/check-in uses `8220`** to enrol Elastic Agents and let enrolled agents check in with Fleet Server.

Do not point APM SDKs at Fleet Server `:8220`, and do not point Fleet enrolment at APM intake `:8200`.

## Why external Compose apps cannot resolve DataObs names by default

Docker Compose creates an isolated project network for each Compose project. Containers can resolve service names and container names only on networks they are attached to.

The DataObs POC stack uses the `dataobs-poc` Docker network and stable container names such as `dataobs-poc-elastic-agent` and `dataobs-poc-fleet-server`. A different Compose project, for example `skillradar_default`, is not automatically attached to `dataobs-poc`. Its containers therefore cannot resolve DataObs-only DNS names until they join the DataObs network.

A common symptom is Docker's embedded DNS server returning an error like:

```text
lookup fleet-server on 127.0.0.11:53: no such host
```

That means the container is asking Docker DNS for a name that does not exist on any network attached to that container.

## One-command connection helper

Start the DataObs POC first:

```bash
./scripts/demo_up.sh
```

Then connect one or more already-running external app containers to the DataObs network:

```bash
./scripts/connect_external_stack.sh <container-name> [container-name ...]
```

Example:

```bash
./scripts/connect_external_stack.sh skillradar-api-1 skillradar-worker-1
```

The helper:

1. Uses `dataobs-poc` by default.
2. Allows override with `DATAOBS_NETWORK`.
3. Verifies the Docker network exists.
4. Verifies every requested container exists.
5. Connects each container only if it is not already connected.
6. Prints the stable DataObs DNS endpoints and example APM environment variables.

If your network has a custom name:

```bash
DATAOBS_NETWORK=my-dataobs-network ./scripts/connect_external_stack.sh skillradar-api-1
```

You can also print endpoint reminders without changing Docker state:

```bash
./scripts/dataobs_endpoints.sh
```

## Correct Elastic APM configuration

Configure APM SDKs inside external app containers with the DataObs APM intake endpoint on **port 8200**:

```env
ELASTIC_APM_SERVER_URL=http://dataobs-poc-elastic-agent:8200
ELASTIC_APM_SECRET_TOKEN=dataobs_poc_apm_token
ELASTIC_APM_SERVICE_NAME=<your-service-name>
ELASTIC_APM_ENVIRONMENT=poc
```

For OpenTelemetry exporters that send OTLP to the Elastic APM integration, use the same host and port, with the protocol path required by your SDK or collector configuration. The DataObs POC default APM integration is hosted by the `dataobs-poc-elastic-agent` container.

## Correct Fleet configuration

Fleet-managed Elastic Agents should use Fleet Server on **port 8220**:

```env
FLEET_URL=http://dataobs-poc-fleet-server:8220
```

Use this for Elastic Agent enrolment and check-in only. It is not an APM intake URL.

## Example SkillRadar configuration

When SkillRadar runs as a separate Compose app, connect its runtime containers to DataObs DNS after they are running:

```bash
./scripts/connect_external_stack.sh skillradar-api-1 skillradar-worker-1
```

Then configure SkillRadar application telemetry like this:

```env
# SkillRadar product search can still use SkillRadar's own Elasticsearch.
ELASTICSEARCH_URL=http://elasticsearch:9201

# SkillRadar observability goes to DataObs.
ELASTIC_APM_ENABLED=true
ELASTIC_APM_SERVICE_NAME=skillradar-api
ELASTIC_APM_SERVER_URL=http://dataobs-poc-elastic-agent:8200
ELASTIC_APM_SECRET_TOKEN=dataobs_poc_apm_token
ELASTIC_APM_ENVIRONMENT=local-demo
ELASTIC_APM_SERVICE_VERSION=0.1.0
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0
ELASTIC_APM_CAPTURE_BODY=off
ELASTIC_APM_CAPTURE_HEADERS=true
```

If SkillRadar also runs a Fleet-managed Elastic Agent container for logs or metrics collection, connect that agent container to `dataobs-poc` and enrol it with:

```env
FLEET_URL=http://dataobs-poc-fleet-server:8220
```

## Troubleshooting

### `lookup fleet-server on 127.0.0.11:53: no such host`

Cause: the external container is not attached to the DataObs network, or it is using the short Compose service name `fleet-server` from outside the DataObs Compose project.

Fix:

```bash
./scripts/connect_external_stack.sh <container-name>
```

Then use the stable container DNS name:

```env
FLEET_URL=http://dataobs-poc-fleet-server:8220
```

### `lookup dataobs-poc-elastic-agent on 127.0.0.11:53: no such host`

Cause: the external container is not attached to `dataobs-poc`, or DataObs is not running.

Fix:

```bash
./scripts/demo_up.sh
./scripts/connect_external_stack.sh <container-name>
```

Then configure APM with:

```env
ELASTIC_APM_SERVER_URL=http://dataobs-poc-elastic-agent:8200
```

### Connection refused on `:8200`

Cause: the Elastic Agent/APM container is not healthy yet, APM is still starting, or the app is pointing to the wrong container/port.

Fix:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc ps
./scripts/dataobs_endpoints.sh
```

Confirm APM uses `http://dataobs-poc-elastic-agent:8200`.

### Connection refused or enrolment failure on `:8220`

Cause: Fleet Server is not healthy yet, the enrolment token/config is wrong, or the app is using the APM endpoint instead of Fleet Server.

Fix:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc ps
./scripts/dataobs_endpoints.sh
```

Confirm Fleet uses `http://dataobs-poc-fleet-server:8220`.

### Verify a container is attached

```bash
docker inspect <container-name> --format '{{json .NetworkSettings.Networks}}'
```

The output should include `dataobs-poc`.
