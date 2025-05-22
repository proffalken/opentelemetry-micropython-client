import logging

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, SpanKind
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject

import requests

HTTP_URL = "http://<EMBEDDED_DEVICE_IP>:8080/"
OTEL_COLLECTOR_URL = "http://<OTEL_COLLECTOR_HOST>:4318/v1/traces"
OTEL_LOGS_URL = "http://<OTEL_COLLECTOR_HOST>:4318/v1/logs"

# Instrument logging (this must be done before logging is configured)
LoggingInstrumentor().instrument(set_logging_format=True)

# Standard Python logging setup
logging.basicConfig(level=logging.INFO)

resource = Resource(attributes={
    SERVICE_NAME: "python3-http-client",
    "namespace": "my-app-namespace"
})

# Tracing setup
tracer_provider = TracerProvider(resource=resource)
set_tracer_provider(tracer_provider)
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_COLLECTOR_URL)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)
tracer = get_tracer_provider().get_tracer("examples/send_http_trace_context")

def main():
    with tracer.start_as_current_span("http-client-span", kind=SpanKind.CLIENT) as span:
        headers = {}
        inject(headers)
        logging.info(f"Sending GET to {HTTP_URL} with headers: {headers}")
        response = requests.get(HTTP_URL, headers=headers)
        logging.info(f"Response: {response.status_code}\n{response.text}")

if __name__ == "__main__":
    main()
