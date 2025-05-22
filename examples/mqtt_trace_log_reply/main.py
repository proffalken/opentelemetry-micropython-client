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
    "service.name": "mqtt-request-response-device",
    "service.version": "0.1",
    "host.name": "esp32-mqtt-request-response"
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
MQTT_PASS = "<MQTT_PASSWORD>"
MQTT_REQUEST_TOPIC = "example/request"
MQTT_RESPONSE_TOPIC = "example/response"

class MsgWrapper:
    """Wraps a message to provide a .data attribute to match OTEL client expectations."""
    def __init__(self, msg):
        self.data = msg

def mqtt_callback(topic, msg):
    try:
        # 1. Extract incoming context
        msg_obj = MsgWrapper(msg)
        payload = ujson.loads(msg_obj.data)
        ctx = otel.extract_context_from_payload(payload)
        parent_trace_id = ctx.get("trace_id")
        parent_span_id = ctx.get("parent_span_id")
        print("Extracted context from payload:", ctx)

        # 2. Start a new child span using extracted context as parent
        span_name = "mqtt_request_received"
        trace_id, span_id = otel.start_trace(
            name=span_name,
            kind="CONSUMER",
            parent_trace_id=parent_trace_id,
            parent_span_id=parent_span_id,
            attributes=[
                {"key": "mqtt.topic", "value": {"stringValue": topic.decode()}},
                {"key": "event", "value": {"stringValue": "mqtt_request_receive"}}
            ]
        )

        # 3. Do "something" with the payload (for example, upper-case a field called "payload")
        request_data = payload.get("payload", "")
        print("Received payload:", request_data)
        processed_data = str(request_data).upper()
        print("Processed payload:", processed_data)

        # 4. End the incoming span
        otel.end_trace(span_id)

        # 5. Start a "PRODUCER" span for the outgoing response
        response_span_name = "mqtt_response_send"
        response_trace_id, response_span_id = otel.start_trace(
            name=response_span_name,
            kind="PRODUCER",
            parent_trace_id=trace_id,  # link to previous
            parent_span_id=span_id,
            attributes=[
                {"key": "mqtt.topic", "value": {"stringValue": MQTT_RESPONSE_TOPIC}},
                {"key": "event", "value": {"stringValue": "mqtt_response_send"}}
            ]
        )

        # 6. Build response payload and inject new context
        response_payload = {
            "payload": processed_data,
            "original_request": request_data
        }
        otel.inject_context_to_payload(
            response_payload,
            trace_id=response_trace_id,
            span_id=response_span_id
        )

        # 7. Publish the response message
        client.publish(MQTT_RESPONSE_TOPIC, ujson.dumps(response_payload))
        print("Published response message with context:", response_payload)

        # 8. End the response span
        otel.end_trace(response_span_id)

    except Exception as e:
        print("Failed to process MQTT message:", e)

# Set up MQTT client with credentials
client = MQTTClient("micropython-client", MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASS)
client.set_callback(mqtt_callback)
client.connect()
client.subscribe(MQTT_REQUEST_TOPIC)
print("MQTT client connected and subscribed to request topic.")

try:
    while True:
        client.wait_msg()  # Blocking wait for message
        time.sleep(0.1)
except KeyboardInterrupt:
    client.disconnect()
    print("MQTT client disconnected.")
