import urandom
import urequests
import time
import ujson

try:
    import ntptime
except ImportError:
    ntptime = None

MICROPY_EPOCH_OFFSET = 946684800  # seconds between 1970-01-01 and 2000-01-01

def zfill(s, width):
    s = str(s)
    if len(s) >= width:
        return s
    return "0" * (width - len(s)) + s

def parse_traceparent(traceparent):
    # Example: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    if not traceparent or not isinstance(traceparent, str):
        return None, None
    parts = traceparent.strip().split("-")
    if len(parts) != 4:
        return None, None
    trace_id = parts[1]
    parent_span_id = parts[2]
    return trace_id, parent_span_id

def ensure_str(val):
    print("[ensure_str] called with val:", val, "type:", type(val))
    if isinstance(val, bytes):
        result = val.decode()
        print("[ensure_str] decoded bytes to str:", result)
        return result
    elif isinstance(val, str):
        result = str(val)
        print("[ensure_str] coerced to str:", result)
        return result
    elif val is None:
        print("[ensure_str] got None, returning ''")
        return ""
    else:
        result = str(val)
        print("[ensure_str] coerced unknown type to str:", result)
        return result

class OpenTelemetryClient:
    def __init__(self, wifi, otel_collector, port=4318, resource_attributes=None, sync_time=True):
        self.wifi = wifi
        self.otel_collector = otel_collector
        self.port = port
        self.trace_id = self.generate_trace_id()
        self.parent_span_id = None
        self.resource_attributes = resource_attributes or {}
        self.SPAN_KIND_MAP = {
            "SERVER": 2,
            "CLIENT": 3,
            "PRODUCER": 4,
            "CONSUMER": 5,
            "INTERNAL": 1
        }
        self.active_spans = {}
        if sync_time:
            self.sync_time()

    def sync_time(self):
        if ntptime is None:
            print("ntptime module not available, cannot sync time.")
            return
        for attempt in range(5):
            try:
                ntptime.settime()
                print("NTP time set.")
                break
            except Exception as e:
                print("Failed to set NTP time, retrying...", e)
                time.sleep(2)
        t = time.localtime()
        print("Current system time after NTP sync:", t)
        if t[0] < 2020:
            print("⚠️  Warning: System time still invalid! Traces may have wrong timestamps.")

    def _now_unix_nano(self):
        return int((time.time() + MICROPY_EPOCH_OFFSET) * 1e9)

    def generate_trace_id(self):
        return "".join("{:08x}".format(urandom.getrandbits(32)) for _ in range(4))

    def generate_span_id(self):
        return "".join("{:08x}".format(urandom.getrandbits(32)) for _ in range(2))

    def export_metric(self, name, value, metric_type="gauge", attributes=None, timestamp=None, **kwargs):
        timestamp = timestamp or self._now_unix_nano()
        attributes = [attrib for attrib in (attributes or []) if attrib.get("key") != "net.peer.port"]
        metric = {
            "name": name,
            "unit": "",
        }
        if metric_type == "gauge":
            metric["gauge"] = {
                "dataPoints": [{
                    "timeUnixNano": timestamp,
                    "attributes": attributes,
                    "asInt": int(value)
                }]
            }
        elif metric_type == "sum":
            metric["sum"] = {
                "dataPoints": [{
                    "timeUnixNano": timestamp,
                    "attributes": attributes,
                    "asInt": int(value)
                }],
                "isMonotonic": kwargs.get("isMonotonic", True),
                "aggregationTemporality": kwargs.get("aggregationTemporality", 2)
            }
        elif metric_type == "histogram":
            metric["histogram"] = {
                "dataPoints": [{
                    "timeUnixNano": timestamp,
                    "attributes": attributes,
                    "count": kwargs.get("count", 1),
                    "sum": kwargs.get("sum", value),
                    "bucketCounts": kwargs.get("bucketCounts", []),
                    "explicitBounds": kwargs.get("explicitBounds", [])
                }],
                "aggregationTemporality": kwargs.get("aggregationTemporality", 2)
            }
        else:
            raise ValueError("Unsupported metric_type: %s" % metric_type)

        data = {
            "resourceMetrics": [{
                "resource": {"attributes": self.format_attributes(self.resource_attributes)},
                "scopeMetrics": [{
                    "scope": {"name": "micropython-client"},
                    "metrics": [metric]
                }]
            }]
        }
        self._send_data("/v1/metrics", data)

    def send_gauge_metric(self, name, value, attributes=None, timestamp=None):
        self.export_metric(name, value, metric_type="gauge", attributes=attributes, timestamp=timestamp)

    def send_counter_metric(self, name, value, attributes=None, timestamp=None):
        self.export_metric(
            name, value, metric_type="sum", attributes=attributes, timestamp=timestamp,
            isMonotonic=True, aggregationTemporality=2
        )

    def send_histogram_metric(self, name, sum_value, count, bucketCounts, explicitBounds, attributes=None, timestamp=None):
        self.export_metric(
            name, sum_value, metric_type="histogram", attributes=attributes, timestamp=timestamp,
            count=count, sum=sum_value, bucketCounts=bucketCounts, explicitBounds=explicitBounds, aggregationTemporality=2
        )

    def start_trace(self, name, kind="CLIENT", attributes=None, parent_trace_id=None, parent_span_id=None):
        print("=== start_trace called ===")
        print("Raw parent_trace_id:", parent_trace_id, "type:", type(parent_trace_id))
        trace_id = parent_trace_id if parent_trace_id else self.generate_trace_id()
        try:
            if isinstance(trace_id, int):
                trace_id = "{:032x}".format(trace_id)
                print("Converted int trace_id to hex:", trace_id)
            elif isinstance(trace_id, str):
                if len(trace_id) == 32 and all(c in "0123456789abcdefABCDEF" for c in trace_id):
                    print("trace_id is already a 32-char hex string:", trace_id)
                elif trace_id.isdigit():
                    print("trace_id is a decimal string, converting to hex...")
                    trace_id = "{:032x}".format(int(trace_id))
                    print("Converted decimal string to hex:", trace_id)
                else:
                    print("trace_id string is not 32-hex or decimal, using as-is:", trace_id)
            else:
                print("trace_id is of unknown type, using as-is:", trace_id)
        except Exception as e:
            print("❌ Error while converting trace_id:", trace_id, e)
            raise

        span_id = self.generate_span_id()
        start_time = self._now_unix_nano()
        kind_lookup_value = self.SPAN_KIND_MAP.get(kind.upper(), 1)
        print(f"Kind Value (string value passed is {kind}): {kind_lookup_value}")
        if attributes is None:
            attributes = []
        print("Received attributes:", attributes)
        self.active_spans[span_id] = {
            "traceId": trace_id,
            "spanId": span_id,
            "parentSpanId": parent_span_id if parent_span_id else "",
            "name": name,
            "kind": kind_lookup_value,
            "startTimeUnixNano": start_time,
            "attributes": self.format_attributes(attributes)
        }
        print(f"✅ Span Created: {name}, Kind: {kind_lookup_value}, traceId: {trace_id}, spanId: {span_id}")
        self.trace_id = trace_id
        self.parent_span_id = span_id
        return trace_id, span_id

    def end_trace(self, span_id):
        if span_id not in self.active_spans:
            print(f"Warning: Attempted to end unknown span {span_id}")
            return
        end_time = self._now_unix_nano()
        span_data = self.active_spans.pop(span_id)
        span_data["endTimeUnixNano"] = end_time + 10000000
        trace_data = {
            "resourceSpans": [{
                "resource": {"attributes": self.format_attributes(self.resource_attributes)},
                "scopeSpans": [{
                    "scope": {"name": "micropython-client"},
                    "spans": [span_data]
                }]
            }]
        }
        self._send_data("/v1/traces", trace_data)

    def log(self, trace_id, span_id, body, attributes=None):
        timestamp = self._now_unix_nano()
        log_data = {
            "resourceLogs": [{
                "resource": {"attributes": self.format_attributes(self.resource_attributes)},
                "scopeLogs": [{
                    "scope": {"name": "micropython-client"},
                    "logRecords": [{
                        "timeUnixNano": timestamp,
                        "TraceId": trace_id,
                        "SpanId": span_id,
                        "body": {"stringValue": str(body)},
                        "attributes": self.format_attributes(attributes or {})
                    }]
                }]
            }]
        }
        self._send_data("/v1/logs", log_data)

    def send_log(self, body, attributes=None, trace_id=None, span_id=None, severity_text="INFO"):
        timestamp = self._now_unix_nano()
        log_record = {
            "timeUnixNano": timestamp,
            "body": {"stringValue": str(body)},
            "attributes": self.format_attributes(attributes or {}),
            "severityText": severity_text,
        }
        if trace_id:
            log_record["TraceId"] = trace_id
        if span_id:
            log_record["SpanId"] = span_id

        log_data = {
            "resourceLogs": [{
                "resource": {"attributes": self.format_attributes(self.resource_attributes)},
                "scopeLogs": [{
                    "scope": {"name": "micropython-client"},
                    "logRecords": [log_record]
                }]
            }]
        }
        self._send_data("/v1/logs", log_data)

    def format_attributes(self, attributes):
        if isinstance(attributes, dict):
            return [{"key": k, "value": {"stringValue": str(v)}} for k, v in attributes.items()]
        elif isinstance(attributes, list):
            return attributes
        else:
            raise TypeError("Attributes must be a list of dictionaries or a dictionary")

    def extract_context_from_payload(self, payload):
        trace_id = None
        parent_span_id = None
        if "traceparent" in payload:
            trace_id, parent_span_id = parse_traceparent(payload["traceparent"])
        else:
            trace_id = payload.get("trace_id")
            parent_span_id = payload.get("parent_span_id")
        ctx = {"trace_id": trace_id, "parent_span_id": parent_span_id}
        print("Extracted context:", ctx)
        return ctx

    def listener_callback(self, msg):
        payload = ujson.loads(msg.data)
        ctx = self.extract_context_from_payload(payload)
        trace_id = ctx.get("trace_id")
        parent_span_id = ctx.get("parent_span_id")
        self.start_trace(
            name="recv_message",
            kind="CONSUMER",
            attributes=[],
            parent_trace_id=trace_id,
            parent_span_id=parent_span_id
        )

    def build_traceparent(self, trace_id, span_id, sampled="01"):
        print("[build_traceparent] called with trace_id:", trace_id, "type:", type(trace_id))
        print("[build_traceparent] called with span_id:", span_id, "type:", type(span_id))
        try:
            trace_id = ensure_str(trace_id or self.trace_id or self.generate_trace_id())
            print("[build_traceparent] after ensure_str(trace_id):", trace_id, "type:", type(trace_id))
            span_id = ensure_str(span_id or self.parent_span_id or self.generate_span_id())
            print("[build_traceparent] after ensure_str(span_id):", span_id, "type:", type(span_id))
            trace_id = zfill(trace_id, 32)
            print("[build_traceparent] after zfill(32) trace_id:", trace_id, "type:", type(trace_id))
            span_id = zfill(span_id, 16)
            print("[build_traceparent] after zfill(16) span_id:", span_id, "type:", type(span_id))
            result = f"00-{trace_id}-{span_id}-{sampled}"
            print("[build_traceparent] result:", result)
            return result
        except Exception as e:
            print("[build_traceparent] Exception occurred:", e)
            try:
                import sys
                print("[build_traceparent] Exception info:", sys.exc_info())
            except Exception:
                pass
            raise

    def inject_context_to_payload(self, payload, trace_id=None, span_id=None, sampled="01"):
        print("[inject_context_to_payload] called with trace_id:", trace_id, "span_id:", span_id)
        traceparent = self.build_traceparent(trace_id, span_id, sampled)
        payload["traceparent"] = traceparent
        payload["trace_id"] = trace_id or self.trace_id
        payload["parent_span_id"] = span_id or self.parent_span_id
        print("[inject_context_to_payload] payload after injection:", payload)
        return payload

    def inject_context_to_headers(self, headers, trace_id=None, span_id=None, sampled="01"):
        print("[inject_context_to_headers] called with trace_id:", trace_id, "span_id:", span_id)
        traceparent = self.build_traceparent(trace_id, span_id, sampled)
        headers["traceparent"] = traceparent
        print("[inject_context_to_headers] headers after injection:", headers)
        return headers

    def _send_data(self, endpoint, data):
        url = f"http://{self.otel_collector}:{self.port}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        print("🔹 Sending Data to OpenTelemetry Collector:")
        print("Data types in outgoing payload:")
        def walk(obj, path=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(v, path + '.' + k if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, f'{path}[{i}]')
            else:
                print(f"{path}: {type(obj)} {repr(obj)}")
        walk(data)
        json_data = ujson.dumps(data)
        print(json_data)
        try:
            response = urequests.post(url, data=json_data, headers=headers)
            print("Raw response content:", getattr(response, "content", "(no .content property)"))
            print("Response:", response.status_code, response.text)
            response.close()
        except Exception as e:
            print("❌ Failed to send data:", e)
