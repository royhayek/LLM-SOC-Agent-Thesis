#!/bin/sh
# Broker entry point (E1-05): build the hashed password file, then run mosquitto.
# credentials.txt holds `user:password` lines; comment lines start with #.
set -eu
grep -v '^#' /mosquitto/config/credentials.txt | grep -v '^$' >/tmp/passwd
mosquitto_passwd -U /tmp/passwd
chown mosquitto:mosquitto /tmp/passwd
chmod 0700 /tmp/passwd
exec mosquitto -c /mosquitto/config/mosquitto.conf
