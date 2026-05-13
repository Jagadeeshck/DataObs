# EC2 OpenTelemetry Agent (Logs + Metrics + Traces)

This guide explains how to run an OpenTelemetry Collector agent on EC2 instances so DataObs can ingest telemetry from any workload running on those hosts (Java, Python, Spark, and other services).

## What this enables

- **Traces** from Java/Python apps via OpenTelemetry SDK/auto-instrumentation over OTLP (4317/4318).
- **Metrics** from app SDKs and EC2 host metrics (CPU, memory, disk, network).
- **Logs** from local files (`/var/log`, Spark log paths).
- **AWS X-Ray daemon compatibility** through the `awsxray` receiver on UDP 2000.

---


## 0) Push agent install/config via Terraform + SSM

If you want centralized rollout (instead of manual SSH), use the Terraform module:

- `infra/terraform/aws-ec2-otel-agent`

The module creates SSM documents + associations so you can target:

- **group of nodes** by tag (for example all Spark workers), or
- **individual EC2 instances** by explicit instance IDs.

See module usage examples in:

- `infra/terraform/aws-ec2-otel-agent/README.md`

---

## 1) Install collector agent on EC2

You can run either:

- **AWS Distro for OpenTelemetry (ADOT) Collector**, or
- **Upstream OpenTelemetry Collector Contrib**.

Use `config/otel-ec2-agent-config.yaml` as the base agent config and place it on each EC2 host, for example:

```bash
sudo mkdir -p /etc/otel-agent
sudo cp config/otel-ec2-agent-config.yaml /etc/otel-agent/config.yaml
```

Set environment variables used by the config:

```bash
export OTEL_GATEWAY_ENDPOINT="otel-gateway.company.net:4317"
export OTEL_GATEWAY_INSECURE="false"
export OTEL_TENANT_ID="data-platform"
export DEPLOYMENT_ENV="prod"
```

---

## 2) Enable Java instrumentation on EC2 workloads

For Java services (including Spark JVM processes), use the OpenTelemetry Java agent:

```bash
export OTEL_SERVICE_NAME="spark-driver"
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=dataobs,deployment.environment.name=prod"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4317"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_METRICS_EXPORTER="otlp"
export OTEL_LOGS_EXPORTER="otlp"

JAVA_TOOL_OPTIONS="-javaagent:/opt/opentelemetry/opentelemetry-javaagent.jar" \
  /path/to/java-or-spark-command
```

For Spark, apply similar environment variables in `spark-env.sh` or job launcher settings for driver/executor processes.

---

## 3) Enable Python instrumentation on EC2 workloads

```bash
export OTEL_SERVICE_NAME="python-etl"
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=dataobs,deployment.environment.name=prod"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4317"

opentelemetry-instrument python your_job.py
```

---

## 4) AWS X-Ray daemon option (supported)

If you still have applications emitting to X-Ray daemon/UDP format, keep that flow and receive it with the collector:

- Open UDP **2000** from local workloads to the collector process.
- Keep `awsxray` receiver enabled in the EC2 agent config.
- Security groups and host firewall must allow local UDP/2000 traffic.

This allows a migration path where some apps use OTLP directly while others continue to emit X-Ray traffic.

---

## 5) Validation checklist

On each EC2 instance:

```bash
# Collector health
curl -sf http://127.0.0.1:13133/

# Confirm OTLP receiver is listening
ss -lntup | grep -E ':4317|:4318|:2000'

# Optional: inspect collector logs
sudo journalctl -u otel-agent -n 200 --no-pager
```

At central DataObs/Elasticsearch:

```bash
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-logs*/_count"
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-metrics*/_count"
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-traces*/_count"
```

If logs/metrics are visible but traces are missing, check:

- app exporter endpoint (`127.0.0.1:4317`),
- X-Ray UDP/2000 reachability,
- and whether the central gateway accepts trace pipeline traffic.
