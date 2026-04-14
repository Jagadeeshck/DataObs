# DataObs — AWS Lambda OTel Layer

Auto-instrument Lambda functions in data pipelines with OTel traces,
metrics, and structured logs using the `@otel_lambda` decorator.

## Usage

```python
from layer.otel_lambda import otel_lambda

@otel_lambda
def handler(event, context):
    # Your Lambda code here
    return {"statusCode": 200}
```

## Attributes emitted

| Attribute | Description |
|-----------|-------------|
| `faas.name` | Lambda function name |
| `faas.coldstart` | True on first invocation |
| `faas.trigger` | http / pubsub / datasource / other |
| `faas.invocation_id` | AWS request ID |
| `cloud.region` | AWS region |

## Build Layer

```bash
cd integrations/aws-lambda/layer
pip install -r requirements.txt -t python/
zip -r dataobs-otel-layer.zip python/
```

Resolves: [#28](https://github.com/Jagadeeshck/DataObs/issues/28)
