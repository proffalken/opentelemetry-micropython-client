import time
from wifi_connection import WiFiConnection
from opentelemetry_client import OpenTelemetryClient

# --- 1. Connect to WiFi ---
SSID = "<YOUR_WIFI_SSID>"
PASSWORD = "<YOUR_WIFI_PASSWORD>"
wifi = WiFiConnection(SSID, PASSWORD)

# --- 2. Set up OpenTelemetry client ---
OTEL_COLLECTOR = "<YOUR_OTEL_COLLECTOR_IP_OR_HOSTNAME>"
RESOURCE_ATTRIBUTES = {
    "service.name": "example-device",
    "service.version": "0.1",
    "host.name": "esp32-example"
}
otel = OpenTelemetryClient(
    wifi,
    otel_collector=OTEL_COLLECTOR,
    resource_attributes=RESOURCE_ATTRIBUTES
)

# --- 3. Send a gauge metric ---
otel.send_gauge_metric(
    name="temperature",
    value=24,
    attributes=[
        {"key": "unit", "value": {"stringValue": "celsius"}}
    ]
)

# --- 4. Start a trace/span, log an event, and end the span ---
trace_id, span_id = otel.start_trace(
    name="example-trace",
    kind="INTERNAL",
    attributes=[
        {"key": "example", "value": {"stringValue": "demo-span"}}
    ]
)

# Simulate some work
time.sleep(1)

# Log an event attached to the span
otel.log(
    trace_id=trace_id,
    span_id=span_id,
    body="This is an example log message from MicroPython",
    attributes={"severity": "info"}
)

# End the span/trace
otel.end_trace(span_id)

print("Example complete! Metric, log, and trace have been sent.")
