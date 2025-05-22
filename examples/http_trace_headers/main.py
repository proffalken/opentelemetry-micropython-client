import uasyncio as asyncio
import time
from wifi_client import WiFiConnection
from opentelemetry_client import OpenTelemetryClient
from machine import Pin

# --- 1. Connect to WiFi ---
SSID = "<SSID>"
PASSWORD = "<PASSWORD>"
wifi = WiFiConnection(SSID, PASSWORD)

# --- 2. Set up OpenTelemetry client ---
OTEL_COLLECTOR = "<COLLECTOR_HOST>:4318"
RESOURCE_ATTRIBUTES = {
    "service.name": "http-device",
    "service.version": "0.1",
    "host.name": "esp32-http",
    "namespace": "your-namespace-here"
}
otel = OpenTelemetryClient(
    wifi,
    otel_collector=OTEL_COLLECTOR,
    resource_attributes=RESOURCE_ATTRIBUTES
)

# --- 3. Simple HTTP server that uses traceparent from headers ---
class SimpleHTTPServer:
    def __init__(self, otel_client, port=8080):
        self.otel_client = otel_client
        self.port = port
        self.led = Pin(2, Pin.OUT)  # GPIO2 for LED

    async def handle_request(self, reader, writer):
        request_line = await reader.readline()
        headers = {}
        while True:
            header_line = await reader.readline()
            if header_line == b"\r\n":
                break
            if b": " in header_line:
                key, value = header_line.decode().strip().split(": ", 1)
                headers[key.lower()] = value

        traceparent = headers.get("traceparent")
        ctx = self.otel_client.extract_context_from_payload({"traceparent": traceparent} if traceparent else {})
        trace_id = ctx.get("trace_id")
        parent_span_id = ctx.get("parent_span_id")

        span_name = "http_request"
        trace_id, span_id = self.otel_client.start_trace(
            name=span_name,
            kind="SERVER",
            parent_trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=[
                {"key": "http.method", "value": {"stringValue": "GET"}},
                {"key": "event", "value": {"stringValue": "http_receive"}}
            ]
        )

        # Log the request (trace- and span-linked)
        self.otel_client.log(
            trace_id=trace_id,
            span_id=span_id,
            body="HTTP request received",
            attributes={"source": "http"}
        )

        # Standalone device log (not tied to a span)
        self.otel_client.send_log(
            body="HTTP server handled a request",
            attributes={
                "http.method": "GET",
                "remote": headers.get("host", "<unknown>")
            },
            severity_text="INFO"
        )

        # Export a simple gauge metric for demo (e.g. always sends 1, could be request count)
        self.otel_client.send_gauge_metric("http_requests", 1, attributes=[
            {"key": "http.method", "value": {"stringValue": "GET"}}
        ])

        self.otel_client.end_trace(span_id)
        response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nTrace received!"
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_request, "0.0.0.0", self.port)
        print("HTTP server running on port", self.port)
        # Send a boot log on startup
        self.otel_client.send_log(
            body="HTTP server started and ready",
            attributes={"listen.port": str(self.port)},
            severity_text="INFO"
        )
        while True:
            await asyncio.sleep(1)

# --- 4. Run the server ---
server = SimpleHTTPServer(otel)
try:
    asyncio.run(server.start())
except KeyboardInterrupt:
    print("HTTP server stopped.")
    otel.send_log(
        body="HTTP server stopped (KeyboardInterrupt)",
        attributes={"listen.port": str(server.port)},
        severity_text="INFO"
    )
