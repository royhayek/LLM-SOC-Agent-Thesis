#!/bin/sh
# Merge the run's per-host pcaps into raw.pcap, in timestamp order (ADR-0009).
# `make down` runs it in the capture image, with the run's flows/ folder mounted at /out.
#
# tcpslice 1.5 stops with "error reading packet" on a pcap that holds no packet (only the
# 24-byte file header), which is what a host that sent nothing leaves behind (the honeypot,
# in a run with no attack on it). Only pcaps with at least one packet are merged. If no host
# sent anything, the first header-only pcap is copied, so raw.pcap is still a valid pcap.
set -eu
cd /out

set --
for f in hosts/*.pcap; do
  [ -f "$f" ] || { echo "no per-host pcap in /out/hosts" >&2; exit 1; }
  if [ "$(wc -c <"$f")" -gt 24 ]; then set -- "$@" "$f"; fi
done

if [ "$#" -eq 0 ]; then
  cp "$(ls hosts/*.pcap | head -n 1)" raw.pcap
else
  tcpslice -w raw.pcap "$@"
fi
echo "merged $# per-host pcaps with packets into raw.pcap"
