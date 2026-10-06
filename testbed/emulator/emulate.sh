#!/bin/sh
# Benign MQTT device emulator (ticket E1-05). Replays this device's seeded plan.
#
# `make up` writes the plan from testbed/profiles/benign.yaml into the run folder
# (thesis/testbed/benign.py); it is mounted at /plan. This script only replays it, so the
# same seed gives the same messages at the same offsets in every run.
#
#   /plan/<DEVICE_ID>.topics  one line per topic: index, topic, QoS
#   /plan/<DEVICE_ID>.plan    one line per event: offset_ms, action, topic index, payload
#     pub        publish the payload on the topic's persistent connection
#     reconnect  drop every connection and open it again (benign irregularity)
#     badauth    one CONNECT with a wrong password, refused by the broker (benign irregularity)
#
# Each topic keeps one persistent connection (`mosquitto_pub -l` reading a FIFO), as a real
# device keeps its session. Runs in the eclipse-mosquitto image, so it needs no MQTT library.
set -eu

: "${DEVICE_ID:?DEVICE_ID is required}"
: "${PASSWORD:?PASSWORD is required}"
BROKER="${BROKER:-broker}"
PLAN="/plan/${DEVICE_ID}.plan"
TOPICS="/plan/${DEVICE_ID}.topics"
[ -f "$PLAN" ] && [ -f "$TOPICS" ] || { echo "no plan for ${DEVICE_ID} in /plan" >&2; exit 1; }

# Stop at once on SIGTERM (as PID 1 the shell otherwise ignores it), so `make down` can
# stop every emulator before the MQTT logger.
trap 'exit 0' TERM

# Capture grace (ADR-0009): this host's capture sidecar can start only after the host, so
# wait before opening any connection, or the opening packets would not be captured.
sleep "${CAPTURE_GRACE_S:-5}" & wait $!

# Topic i writes to file descriptor i+3. Children close 3 and 4, or a connection's FIFO
# would keep a writer after a reconnect and its reader would never see end of file.
open_conn() {
  set -- $(sed -n "$(($1 + 1))p" "$TOPICS")  # index topic qos
  fifo="/tmp/topic$1"
  rm -f "$fifo" && mkfifo "$fifo"
  mosquitto_pub -h "$BROKER" -u "$DEVICE_ID" -P "$PASSWORD" -i "${DEVICE_ID}-t$1" \
    -q "$3" -t "$2" -l <"$fifo" 3>&- 4>&- &
  eval "pid$1=\$!"
  eval "exec $(($1 + 3))>\"\$fifo\""
}

close_conn() {
  eval "exec $(($1 + 3))>&-"
  eval "wait \$pid$1" || true
}

n_topics=$(wc -l <"$TOPICS")
for_each_topic() {
  i=0
  while [ "$i" -lt "$n_topics" ]; do "$1" "$i"; i=$((i + 1)); done
}

# Start 0.3 s after a whole second of the wall clock. Plan offsets are whole seconds (a
# burst adds at most 0.4 s), so every message lands in the logged second its offset names:
# the MQTT log has one-second resolution.
s0=$(date +%s)
while [ "$(date +%s)" = "$s0" ]; do usleep 10000; done
start=$(awk '{ printf "%.2f", $1 + 0.3 }' /proc/uptime)

for_each_topic open_conn

while read -r offset action arg payload; do
  # Deadline from the start, on the container's monotonic clock: no drift between events.
  delay=$(awk -v s="$start" -v o="$offset" '{ w = s + o / 1000 - $1; printf "%.3f", (w > 0 ? w : 0) }' /proc/uptime)
  sleep "$delay" & wait $!
  case "$action" in
    pub) eval "printf '%s\n' \"\$payload\" >&$((arg + 3))" ;;
    reconnect) for_each_topic close_conn; for_each_topic open_conn ;;
    badauth)
      mosquitto_pub -h "$BROKER" -u "$DEVICE_ID" -P "wrong-${PASSWORD}" -i "${DEVICE_ID}-auth" \
        -t "iot/${DEVICE_ID}/status" -m auth 3>&- 4>&- >/dev/null 2>&1 || true ;;
    *) echo "unknown plan action: $action" >&2; exit 1 ;;
  esac
done <"$PLAN"

# Plan finished: stay connected and idle until stopped.
while true; do sleep 3600 & wait $!; done
