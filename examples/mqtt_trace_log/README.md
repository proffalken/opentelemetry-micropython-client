# MQTT Trace Log Example Client

This example demonstrates how to:
- Generate a W3C-compliant trace ID using the official OpenTelemetry Python SDK.
- Log with OTEL logging and export traces/logs to an OTEL Collector over HTTP.
- Send a JSON message containing the trace ID and a payload over MQTT.

## Requirements

- Python 3.7+
- MQTT broker (e.g. Mosquitto)
- OpenTelemetry Collector (listening on http://localhost:4318 by default)

### Python dependencies

```sh
pip install paho-mqtt opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-exporter-otlp-proto-http
```

## Usage

1. Ensure your OpenTelemetry Collector is running and listening at `http://localhost:4318`.
2. Ensure your MQTT broker is running and accessible (default: `localhost`).
3. Edit the script to update `MQTT_BROKER`, `MQTT_TOPIC`, or `OTEL_COLLECTOR_URL` if needed.
4. Run the client:

```sh
python send_mqtt_trace_log.py
```

## What It Does

- Generates a trace ID using the OpenTelemetry SDK.
- Sends a JSON message with the trace ID and payload to the MQTT topic.
- Exports the trace and log to your OTEL Collector via HTTP.

You can observe the traces/logs in your collector backend (e.g. Jaeger, Tempo, etc).
