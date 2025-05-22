import time
import json
import threading
import os
import paho.mqtt.client as mqtt

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.propagate import inject, extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# --- OTEL SETUP ---
OTEL_COLLECTOR_URL = os.environ.get("OTEL_COLLECTOR_URL", "localhost:4318")
OTEL_ENDPOINT = f"http://{OTEL_COLLECTOR_URL}/v1/traces"

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: "python3-otel-mqtt-client"})
    )
)
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint=OTEL_ENDPOINT
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# --- MQTT SETUP ---
MQTT_BROKER = os.environ.get("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER", "username")
MQTT_PASS = os.environ.get("MQTT_PASS", "password")
MQTT_REQUEST_TOPIC = os.environ.get("MQTT_REQUEST_TOPIC", "example/request")
MQTT_RESPONSE_TOPIC = os.environ.get("MQTT_RESPONSE_TOPIC", "example/response")
CLIENT_ID = f"python3-otel-client-{int(time.time())}"

response_received = threading.Event()
response_payload = {}

def on_connect(client, userdata, flags, reasonCode, properties=None):
    print("Connected with reason code", reasonCode)
    client.subscribe(MQTT_RESPONSE_TOPIC)

def on_message(client, userdata, msg):
    global response_payload
    payload = json.loads(msg.payload.decode())
    print("Received response:", payload)
    # Extract context from MQTT payload
    carrier = payload
    ctx = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span(
        "process_response",
        context=ctx,
        kind=SpanKind.CONSUMER
    ) as span:
        span.set_attribute("mqtt.topic", MQTT_RESPONSE_TOPIC)
        result = payload.get("payload")
        print(f"Processed response payload: {result}")
        response_payload = payload
        response_received.set()

def main():
    print(f"Using OTEL Collector URL: {OTEL_COLLECTOR_URL}")
    print(f"OTEL Exporter endpoint: {OTEL_ENDPOINT}")
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv5)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    # Give some time for MQTT to connect and subscribe
    time.sleep(1)

    # ---- Start the OTEL trace for the request ----
    with tracer.start_as_current_span(
        "send_request",
        kind=SpanKind.PRODUCER
    ) as span:
        span.set_attribute("mqtt.topic", MQTT_REQUEST_TOPIC)
        message_payload = {"payload": "hello from python3 client"}
        # Inject context into payload using W3C traceparent
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier)
        # Add trace context to payload (as traceparent)
        message_payload.update(carrier)
        print("Publishing message with payload:", message_payload)
        client.publish(MQTT_REQUEST_TOPIC, json.dumps(message_payload))
        span.add_event("Request published")

    # Wait for response (with timeout)
    if not response_received.wait(timeout=10):
        print("No response received in time.")
    else:
        print("Response handling complete.")

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
