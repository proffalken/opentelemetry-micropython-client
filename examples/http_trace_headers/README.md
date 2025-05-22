# HTTP Trace ID Header Example Client

This example demonstrates how to:
- Generate a W3C-compliant trace ID using the official OpenTelemetry Python SDK.
- Log with OTEL logging and export traces/logs to an OTEL Collector over HTTP.
- Send an HTTP GET request with the generated trace ID in an `X-TraceId` header.

## Requirements

- Python 3.7+
- OpenTelemetry Collector (listening on http://localhost:4318 by default)
- An HTTP server (e.g. MicroPython device) that consumes the `X-TraceId` header.

### Python dependencies

```sh
pip install requests opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-exporter-otlp-proto-http
```

## Usage

1. Ensure your OpenTelemetry Collector is running and listening at `http://localhost:4318`.
2. Ensure the target HTTP server is running and accessible (default: `http://localhost:8080/`).
3. Edit the script to update `HTTP_URL` or `OTEL_COLLECTOR_URL` if needed.
4. Run the client:

```sh
python send_http_traceid_header.py
```

## What It Does

- Generates a trace ID using the OpenTelemetry SDK.
- Sends an HTTP GET to the configured URL, passing the trace ID in `X-TraceId`.
- Exports the trace and log to your OTEL Collector via HTTP.

You can observe the traces/logs in your collector backend (e.g. Jaeger, Tempo, etc).
