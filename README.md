# OpenTelemetry MicroPython Client

[![License](https://img.shields.io/github/license/proffalken/opentelemetry-micropython-client)](LICENSE)

A lightweight OpenTelemetry client library for [MicroPython](https://micropython.org/) that brings distributed tracing, metrics, and observability to embedded and IoT Python devices. Built specifically for MicroPython environments, this library enables you to instrument your projects and export telemetry data to any OpenTelemetry-compatible backend.

## Features

- **Tracing**: Create, manage, and export traces and spans from MicroPython applications.
- **Metrics**: Send custom metrics such as gauge values.
- **Logging**: Log events tied to traces/spans.
- **Context Propagation**: Maintain trace context across your application.
- **WiFi Client**: Includes a basic, MicroPython-friendly WiFi connection helper for easy network setup (but you can easily add your own!).
- **Example Integrations**: Example code for ESP32 and other MicroPython boards, including HTTP and MQTT trace propagation.

## Getting Started

### 1. Install the Library

- Download or clone this repository.
- Copy the relevant `.py` files (such as `opentelemetry_client.py` and `wifi_connection.py`) into your MicroPython project directory.

#### 1(a). Install via MIP

```
mpremote mip install github:proffalken/opentelemetry-micropython-client
```

#### 1(b). Dependencies

It turns out that different distributions of MicroPython include different sets of libraries.

This means that whilst `umqtt` is included on the ESP32 distribution, it is *not* included on the RP2040
by default and therefore the examples don't work straight away on the Pi Pico W.

To fix this, connect to the Pi Pico W and press `ctrl+c` to get yourself to the command prompt (which 
looks like `>>>`).

Now run the following commands:

```python
import mips
mips.install("umqtt.simple")
```

Now restart the device (`ctrl+d`) does this on my board and the MQTT examples should work!

### 2. Basic Usage Example

Here is a minimal example based on [`examples/basic/main.py`](examples/basic/main.py):

```python
import time
from wifi_connection import WiFiConnection
from opentelemetry_client import OpenTelemetryClient

# 1. Connect to WiFi
SSID = "<YOUR_WIFI_SSID>"
PASSWORD = "<YOUR_WIFI_PASSWORD>"
wifi = WiFiConnection(SSID, PASSWORD)

# 2. Set up OpenTelemetry client
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

# 3. Send a gauge metric
otel.send_gauge_metric(
    name="temperature",
    value=24,
    attributes=[
        {"key": "unit", "value": {"stringValue": "celsius"}}
    ]
)

# 4. Start a trace/span, log an event, and end the span
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
```

### 3. Setting up Networking (MicroPython WiFi)

The included `wifi_connection.py` module provides an easy way to connect your MicroPython device to a WiFi network:

```python
from wifi_connection import WiFiConnection

wifi = WiFiConnection("your-ssid", "your-password")
```

### 4. Exporting Telemetry

All telemetry (metrics, traces, logs) is exported to the OpenTelemetry Collector endpoint you specify.

## More Examples

See the [examples directory](./examples/) for:

- [Basic usage](./examples/basic/main.py)
- [Propagating trace headers over HTTP](./examples/http_trace_headers/)
- [Tracing and logging with MQTT](./examples/mqtt_trace_log/)
- [MQTT trace log with reply](./examples/mqtt_trace_log_reply/)

Each example comes with detailed README and code you can adapt to your own MicroPython projects.

## Project Status

This library is under active development. Contributions, feedback, and issues are welcome!

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

Made with ❤️ for the MicroPython community.
