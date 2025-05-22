import json
import paho.mqtt.client as mqtt

from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, SpanKind
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject  # <-- import this

import logging

MQTT_BROKER = "<MQTT_HOST>"
MQTT_PORT = 1883
MQTT_USER = "<MQTT_USER>"
MQTT_PASS = "<MQTT_PASS>"
MQTT_TOPIC = "test/trace"
OTEL_COLLECTOR_URL = "http://<OTEL_COLLECTOR_HOST>:4318/v1/traces"

# --- OTEL Tracing Setup ---
resource = Resource(attributes={
    SERVICE_NAME: "python3-mqtt-client"
})

tracer_provider = TracerProvider(resource=resource)
set_tracer_provider(tracer_provider)
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_COLLECTOR_URL)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)
tracer = get_tracer_provider().get_tracer("examples/send_mqtt_trace_log")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    with tracer.start_as_current_span("mqtt-client-span", kind=SpanKind.PRODUCER) as span:
        # Prepare payload dict
        payload = {
            "payload": "Hello from standard Python MQTT client with OTEL trace context!"
        }
        # Inject current context into payload (adds 'traceparent' etc.)
        inject(payload)
        # Optionally, also include human-readable trace id for debugging
        payload["debug_trace_id"] = format(span.get_span_context().trace_id, "032x")

        msg = json.dumps(payload)
        logging.info(f"Publishing to {MQTT_TOPIC}: {msg}")
        client.publish(MQTT_TOPIC, msg)
    client.disconnect()

if __name__ == "__main__":
    main()
