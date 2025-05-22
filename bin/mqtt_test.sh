#!/bin/bash

# Example usage:
# ./mqtt_test.sh [collector_host:port] [mqtt_broker] [mqtt_user] [mqtt_pass] [mqtt_request_topic] [mqtt_response_topic]

# Set defaults
OTEL_COLLECTOR_URL="${1:-<OTEL_COLLECTOR_HOST>:4318}"
MQTT_BROKER="${2:-<MQTT_BROKER>}"
MQTT_USER="${3:-<MQTT_USER>}"
MQTT_PASS="${4:-<MQTT_PASS>}"
MQTT_REQUEST_TOPIC="${5:-example/request}"
MQTT_RESPONSE_TOPIC="${6:-example/response}"

export OTEL_COLLECTOR_URL
export MQTT_BROKER
export MQTT_USER
export MQTT_PASS
export MQTT_REQUEST_TOPIC
export MQTT_RESPONSE_TOPIC

echo "OTEL_COLLECTOR_URL=${OTEL_COLLECTOR_URL}"
echo "MQTT_BROKER=${MQTT_BROKER}"
echo "MQTT_USER=${MQTT_USER}"
echo "MQTT_PASS=${MQTT_PASS}"
echo "MQTT_REQUEST_TOPIC=${MQTT_REQUEST_TOPIC}"
echo "MQTT_RESPONSE_TOPIC=${MQTT_RESPONSE_TOPIC}"

python examples/mqtt_trace_log_reply/client.py
