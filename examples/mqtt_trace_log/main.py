import time
import ujson
from wifi_client import WiFiConnection
from opentelemetry_client import OpenTelemetryClient
from umqtt.simple import MQTTClient

# --- 1. Connect to WiFi ---
SSID = "<SSID>"
PASSWORD = "<PASSWORD>"
wifi = WiFiConnection(SSID, PASSWORD)

# --- 2. Set up OpenTelemetry client ---
OTEL_COLLECTOR = "<COLLECTOR_HOST>:4318"
RESOURCE_ATTRIBUTES = {
    "service.name": "mqtt-device",
    "service.version": "0.1",
    "host.name": "esp32-mqtt"
}
otel = OpenTelemetryClient(
    wifi,
    otel_collector=OTEL_COLLECTOR,
    resource_attributes=RESOURCE_ATTRIBUTES,
    sync_time=True
)

# --- 3. MQTT Setup ---
MQTT_BROKER = "<MQTT_HOST>"
MQTT_PORT = 1883
MQTT_USER = "<MQTT_USER>"
MQTT_PASS = "<MQTT_PASS>"
MQTT_TOPIC = "test/trace"

class MsgWrapper:
    """Wraps a message to provide a .data attribute to match OTEL client expectations."""
    def __init__(self, msg):
        self.data = msg

def mqtt_callback(topic, msg):
    try:
        # Wrap the message as expected by the OTEL client
        msg_obj = MsgWrapper(msg)
        # Extract context (trace_id, parent_span_id) from the payload
        ctx = otel.extract_context_from_payload(ujson.loads(msg_obj.data))
        parent_trace_id = ctx.get("trace_id")
        parent_span_id = ctx.get("parent_span_id")
        print("Extracted context from payload:", ctx)

        # Start a new child span using extracted context as parent
        span_name = "mqtt_message_received"
        trace_id, span_id = otel.start_trace(
            name=span_name,
            kind="CONSUMER",
            parent_trace_id=parent_trace_id,
            parent_span_id=parent_span_id,
            attributes=[
                {"key": "mqtt.topic", "value": {"stringValue": topic.decode()}},
                {"key": "event", "value": {"stringValue": "mqtt_receive"}}
            ]
        )

        # Log the message payload
        payload_val = ujson.loads(msg_obj.data).get("payload", "")
        otel.log(
            trace_id=trace_id,
            span_id=span_id,
            body=payload_val,
            attributes={"source": "mqtt"}
        )
        otel.end_trace(span_id)
        print("MQTT message processed and traced.")

    except Exception as e:
        print("Failed to process MQTT message:", e)

# Set up MQTT client with credentials
client = MQTTClient("micropython-client", MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASS)
client.set_callback(mqtt_callback)
client.connect()
client.subscribe(MQTT_TOPIC)
print("MQTT client connected and subscribed.")

try:
    while True:
        client.wait_msg()  # Blocking wait for message
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
    print("MQTT client disconnected.")
