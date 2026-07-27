"""
Sample Python Flask application fully instrumented with OpenTelemetry SDKs.
Emits traces, metrics, and logs — all correlated via trace/span IDs.
Signals are exported via OTLP gRPC to Grafana Alloy on localhost:4317.
"""

import logging
import os
import random
import time

from flask import Flask, jsonify, request

# ── OpenTelemetry core ────────────────────────────────────────────────────────
from opentelemetry import metrics, trace

# ── Logs ──────────────────────────────────────────────────────────────────────
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# ── Auto-instrumentation ──────────────────────────────────────────────────────
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# ── Metrics ───────────────────────────────────────────────────────────────────
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# ── Traces ────────────────────────────────────────────────────────────────────
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# ─────────────────────────────────────────────────────────────────────────────
# Configuration from environment
# ─────────────────────────────────────────────────────────────────────────────
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "sample-python-app")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")

# ─────────────────────────────────────────────────────────────────────────────
# Shared Resource — ties every signal to the same service identity
# ─────────────────────────────────────────────────────────────────────────────
resource = Resource.create(
    {
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "deployment.environment": ENVIRONMENT,
        "service.namespace": "observability-demo",
        "host.name": os.getenv("HOSTNAME", "localhost"),
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# Traces setup
# ─────────────────────────────────────────────────────────────────────────────
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Metrics setup
# ─────────────────────────────────────────────────────────────────────────────
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True),
    export_interval_millis=15_000,  # export every 15 s
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Custom instruments
http_requests_counter = meter.create_counter(
    name="http.server.requests",
    description="Total HTTP requests received",
    unit="1",
)
request_latency_histogram = meter.create_histogram(
    name="http.server.request.duration",
    description="HTTP request duration",
    unit="s",
)
active_requests_gauge = meter.create_up_down_counter(
    name="http.server.active_requests",
    description="Number of in-flight requests",
    unit="1",
)
order_value_histogram = meter.create_histogram(
    name="business.order.value",
    description="Value of orders placed",
    unit="USD",
)

# ─────────────────────────────────────────────────────────────────────────────
# Logs setup — bridge Python logging into OTLP
# ─────────────────────────────────────────────────────────────────────────────
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True))
)
set_logger_provider(logger_provider)

# Attach OTel handler to Python root logger (injects trace_id / span_id)
logging.basicConfig(level=logging.INFO)
otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
logging.getLogger().addHandler(otel_handler)

# Inject trace context into every log record for correlation in Loki
LoggingInstrumentor().instrument(set_logging_format=True)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Flask app + auto-instrumentation
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# ─────────────────────────────────────────────────────────────────────────────
# Simulated in-memory data store
# ─────────────────────────────────────────────────────────────────────────────
PRODUCTS = {
    "P001": {"name": "Widget Alpha", "price": 29.99, "stock": 150},
    "P002": {"name": "Widget Beta", "price": 49.99, "stock": 75},
    "P003": {"name": "Widget Gamma", "price": 9.99, "stock": 300},
}
orders: dict = {}


# ─────────────────────────────────────────────────────────────────────────────
# Middleware — track active requests
# ─────────────────────────────────────────────────────────────────────────────
@app.before_request
def before_request():
    request._start_time = time.time()
    active_requests_gauge.add(1, {"http.method": request.method})


@app.after_request
def after_request(response):
    duration = time.time() - getattr(request, "_start_time", time.time())
    labels = {
        "http.method": request.method,
        "http.route": request.path,
        "http.status_code": str(response.status_code),
    }
    http_requests_counter.add(1, labels)
    request_latency_histogram.record(duration, labels)
    active_requests_gauge.add(-1, {"http.method": request.method})
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.route("/")
def root():
    logger.info("Root endpoint called")
    return jsonify(
        {
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "environment": ENVIRONMENT,
            "endpoints": ["/products", "/orders", "/checkout", "/health", "/simulate-error"],
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": SERVICE_NAME})


@app.route("/products")
def list_products():
    with tracer.start_as_current_span("list-products") as span:
        span.set_attribute("product.count", len(PRODUCTS))
        logger.info("Listing all products", extra={"product_count": len(PRODUCTS)})

        # Simulate DB latency
        time.sleep(random.uniform(0.01, 0.05))

        return jsonify({"products": PRODUCTS, "count": len(PRODUCTS)})


@app.route("/products/<product_id>")
def get_product(product_id: str):
    with tracer.start_as_current_span("get-product") as span:
        span.set_attribute("product.id", product_id)

        product = PRODUCTS.get(product_id)
        if not product:
            span.set_attribute("product.found", False)
            span.set_status(trace.StatusCode.ERROR, "Product not found")
            logger.warning("Product not found", extra={"product_id": product_id})
            return jsonify({"error": "Product not found"}), 404

        span.set_attribute("product.found", True)
        span.set_attribute("product.name", product["name"])
        span.set_attribute("product.price", product["price"])
        logger.info("Product retrieved", extra={"product_id": product_id, "name": product["name"]})
        return jsonify(product)


@app.route("/checkout", methods=["POST"])
def checkout():
    """
    Simulates an order checkout with child spans for validation,
    inventory check, and payment processing — ideal for tracing drilldown.
    """
    with tracer.start_as_current_span("checkout") as root_span:
        data = request.get_json() or {}
        product_id = data.get("product_id", "P001")
        quantity = int(data.get("quantity", 1))

        root_span.set_attribute("order.product_id", product_id)
        root_span.set_attribute("order.quantity", quantity)
        logger.info("Checkout initiated", extra={"product_id": product_id, "quantity": quantity})

        # ── Child span: validate input ────────────────────────────────────
        with tracer.start_as_current_span("validate-order") as val_span:
            time.sleep(random.uniform(0.005, 0.02))
            if quantity <= 0 or quantity > 100:
                val_span.set_status(trace.StatusCode.ERROR, "Invalid quantity")
                root_span.set_status(trace.StatusCode.ERROR, "Validation failed")
                logger.error("Checkout validation failed", extra={"quantity": quantity})
                return jsonify({"error": "Quantity must be between 1 and 100"}), 400
            val_span.set_attribute("validation.passed", True)
            logger.info("Order validation passed")

        # ── Child span: inventory check ───────────────────────────────────
        with tracer.start_as_current_span("check-inventory") as inv_span:
            time.sleep(random.uniform(0.01, 0.04))
            product = PRODUCTS.get(product_id)
            if not product:
                inv_span.set_status(trace.StatusCode.ERROR, "Product not found")
                return jsonify({"error": "Product not found"}), 404
            if product["stock"] < quantity:
                inv_span.set_status(trace.StatusCode.ERROR, "Insufficient stock")
                logger.warning("Insufficient stock", extra={"product_id": product_id, "stock": product["stock"]})
                return jsonify({"error": "Insufficient stock"}), 409
            inv_span.set_attribute("inventory.available", product["stock"])
            logger.info("Inventory check passed", extra={"stock": product["stock"]})

        # ── Child span: process payment ───────────────────────────────────
        with tracer.start_as_current_span("process-payment") as pay_span:
            time.sleep(random.uniform(0.05, 0.15))  # payment takes longer
            total = product["price"] * quantity
            pay_span.set_attribute("payment.total_usd", total)
            pay_span.set_attribute("payment.method", "card")

            # Simulate occasional payment failure (10%)
            if random.random() < 0.10:
                pay_span.set_status(trace.StatusCode.ERROR, "Payment gateway timeout")
                root_span.set_status(trace.StatusCode.ERROR, "Payment failed")
                logger.error("Payment processing failed", extra={"total": total})
                return jsonify({"error": "Payment gateway timeout"}), 502

            pay_span.add_event("payment_authorized", {"amount": total, "currency": "USD"})
            logger.info("Payment processed", extra={"total_usd": total})

        # Deduct stock & record order
        PRODUCTS[product_id]["stock"] -= quantity
        order_id = f"ORD-{len(orders) + 1:04d}"
        orders[order_id] = {
            "id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "total": total,
            "status": "confirmed",
        }

        root_span.set_attribute("order.id", order_id)
        root_span.set_attribute("order.total_usd", total)
        order_value_histogram.record(total, {"product.id": product_id})

        logger.info("Order confirmed", extra={"order_id": order_id, "total_usd": total})
        return jsonify(orders[order_id]), 201


@app.route("/orders")
def list_orders():
    with tracer.start_as_current_span("list-orders") as span:
        span.set_attribute("order.count", len(orders))
        return jsonify({"orders": list(orders.values()), "count": len(orders)})


@app.route("/simulate-error")
def simulate_error():
    """Deliberately raises an error to test alerting and anomaly detection."""
    with tracer.start_as_current_span("simulate-error") as span:
        span.set_status(trace.StatusCode.ERROR, "Intentional error for testing")
        span.add_event("error_simulated", {"reason": "manual trigger"})
        logger.error("Simulated error endpoint triggered — testing anomaly detection")
        return jsonify({"error": "Intentional 500 for observability testing"}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(
        "Starting %s v%s in %s — OTLP endpoint: %s",
        SERVICE_NAME,
        SERVICE_VERSION,
        ENVIRONMENT,
        OTLP_ENDPOINT,
    )
    app.run(host="0.0.0.0", port=5000, debug=False)
