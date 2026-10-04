#!/bin/sh
# Simple periodic MQTT publisher: one benign reading every PERIOD seconds.
# Runs in the eclipse-mosquitto image, so it needs no MQTT library.
# Each reading opens its own connection, so every publish leaves a flow record.
set -eu

: "${DEVICE_ID:?DEVICE_ID is required}"
: "${KIND:?KIND is required}"
BROKER="${BROKER:-broker}"
PERIOD="${PERIOD:-5}"
TOPIC="iot/${DEVICE_ID}/telemetry"
# Stop at once on SIGTERM (as PID 1 the shell otherwise ignores it), so `make down`
# can stop every emulator before the MQTT logger.
trap 'exit 0' TERM

# First reading after one period, so the MQTT logger has subscribed before it.
sleep "$PERIOD" & wait $!

seq_no=0
while true; do
  seq_no=$((seq_no + 1))
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  # awk gives a reading near a fixed base value. The seed is a CRC of device and reading
  # number: BusyBox awk's first rand() rises steadily with consecutive seeds.
  seed=$(printf '%s-%s' "$DEVICE_ID" "$seq_no" | cksum | cut -d' ' -f1)
  value=$(awk -v s="$seed" -v kind="$KIND" 'BEGIN {
    srand(s)
    if (kind == "temperature") base = 21; else if (kind == "humidity") base = 45;
    else if (kind == "power") base = 60; else base = 1
    printf "%.2f", base + (rand() - 0.5) * base * 0.1
  }')
  payload="{\"device_id\":\"${DEVICE_ID}\",\"kind\":\"${KIND}\",\"seq\":${seq_no},\"ts\":\"${ts}\",\"value\":${value}}"
  mosquitto_pub -h "$BROKER" -q 1 -i "$DEVICE_ID" -t "$TOPIC" -m "$payload" \
    || echo "publish failed at seq ${seq_no}" >&2
  sleep "$PERIOD" & wait $!
done
