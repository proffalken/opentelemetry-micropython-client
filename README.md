# opentelemetry-micropython-client

[![MicroPython](https://img.shields.io/badge/MicroPython-Compatible-blue.svg)](https://micropython.org/)
[![MIP Installable](https://img.shields.io/badge/MIP%20Installable-Yes-green)](https://docs.micropython.org/en/latest/reference/packages.html)

A minimal [OpenTelemetry](https://opentelemetry.io/) client for MicroPython, supporting basic metrics, traces, and logs.  
Designed for IoT and embedded devices running MicroPython.

---

## Features

- Send logs, traces, and metrics to an OpenTelemetry Collector over HTTP.
- Log events with trace/span correlation.
- Lightweight, suitable for constrained environments.
- **Installable directly on MicroPython devices via [MIP](https://docs.micropython.org/en/latest/reference/packages.html).**

---

## Installation

### Using mpremote + MIP (recommended)

```sh
mpremote mip install github:proffalken/opentelemetry-micropython-client
```

Or, to install just the library file:

```sh
mpremote mip install https://raw.githubusercontent.com/proffalken/opentelemetry-micropython-client/main/opentelemetry_client.py
```

> Replace `proffalken` and the repo name if you fork or rename.

---

## Usage

```python
from opentelemetry_client import OpenTelemetryClient

# Example: set up your WiFi and resource attributes as needed
wifi = None  # (Replace with your WiFi connection instance)
otel = OpenTelemetryClient(
    wifi,
    otel_collector="192.168.1.100",
    resource_attributes={
        "service.name": "my-device",
        "host.name": "esp32"
    }
)

# Start a trace
trace_id, span_id = otel.start_trace("my-span", kind="SERVER")
# ... do something ...
otel.send_gauge_metric("temperature", 22)
otel.log(trace_id, span_id, "Something happened")
otel.end_trace(span_id)
```

See [opentelemetry_client.py](opentelemetry_client.py) for API details.

---

## Development

Clone the repo, edit `opentelemetry_client.py`, and test on your MicroPython device.

To update the package via MIP, push to the `main` branch.

---

## License

MIT License.

---

## References

- [MicroPython MIP packaging](https://docs.micropython.org/en/latest/reference/packages.html)
- [OpenTelemetry documentation](https://opentelemetry.io/)
