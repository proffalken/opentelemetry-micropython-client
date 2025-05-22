# Example Applications

This directory contains example applications for using and testing the MicroPython OpenTelemetry client and their standard Python3 counterparts.

## Structure

Each example is in its own subdirectory and contains:

- `main.py` – MicroPython/embedded device code.
- `send_*.py` – Python3 client to interact with the device and generate traces/metrics/logs.
- `send_*.md` – Dedicated README for the Python3 client.

## Examples

- `basic_usage/` – Minimal example: connect to WiFi, import the library, and send a gauge metric, trace, and log.
- `mqtt_trace_log/` – Receive a message over MQTT, extract trace ID, trace and log the message.
- `mqtt_trace_log_reply/` – Like above, but also replies over MQTT with the trace ID.
- `http_traceid_header/` – Receive an HTTP request, extract trace ID from a header, and trace/log.

See each subdirectory's README for details.

---
