#!/usr/bin/env bash
# Egress check for the testbed (ticket E0-07, record §6.11).
#
# For every running testbed container, a throwaway busybox probe joins that container's
# network namespace and tries to reach 1.1.1.1, the host LAN gateway and Docker's host
# gateway (by ICMP ping and by TCP on ports 53, 80 and 443).
#
# Exit 0: every container failed to reach every target.
# Exit 1: some container reached some target. The testbed is NOT isolated.
# Exit 2: the check could not run (no testbed, no LAN gateway, or the control failed).
#
# Control: the same probe first runs on Docker's default bridge network, where the targets
# must be reachable. A probe that cannot reach anything from there proves nothing.
set -euo pipefail

PROJECT="thesis-testbed"
PROBE_IMAGE="busybox:1.37.0"
INTERNET_TARGET="1.1.1.1"

lan_gateway() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    route -n get default 2>/dev/null | awk '/gateway:/ {print $2}'
  else
    ip route show default 2>/dev/null | awk '/default/ {print $3; exit}'
  fi
}

# Docker's own route to the host (on Docker Desktop, the VM's host gateway).
docker_host_gateway() {
  docker run --rm --add-host "probe-host:host-gateway" "$PROBE_IMAGE" \
    awk '$2 == "probe-host" {print $1}' /etc/hosts
}

# Prints REACHABLE or UNREACHABLE for one target, from the given --network value.
probe() {
  local network="$1" target="$2"
  docker run --rm --network "$network" "$PROBE_IMAGE" sh -c '
    t="$1"
    if ping -c 1 -W 2 "$t" >/dev/null 2>&1; then echo REACHABLE; exit 0; fi
    for port in 53 80 443; do
      if nc -z -w 2 "$t" "$port" >/dev/null 2>&1; then echo REACHABLE; exit 0; fi
    done
    echo UNREACHABLE
  ' probe "$target"
}

docker pull -q "$PROBE_IMAGE" >/dev/null

gateway="$(lan_gateway)"
if [[ -z "$gateway" ]]; then
  echo "ERROR: could not find the host LAN gateway." >&2
  exit 2
fi
host_gateway="$(docker_host_gateway)"
targets=("$INTERNET_TARGET" "$gateway" "$host_gateway")
echo "Targets: internet $INTERNET_TARGET, LAN gateway $gateway, Docker host gateway $host_gateway"

containers=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}' | sort)
if [[ -z "$containers" ]]; then
  echo "ERROR: no running $PROJECT containers. Run 'make up' first." >&2
  exit 2
fi

echo "Control (default bridge network, targets must be reachable):"
for t in "${targets[@]}"; do
  result=$(probe bridge "$t")
  echo "  $t: $result"
  if [[ "$result" != "REACHABLE" ]]; then
    echo "ERROR: the control cannot reach $t, so the probe cannot show isolation." >&2
    exit 2
  fi
done

leaks=0
for c in $containers; do
  for t in "${targets[@]}"; do
    result=$(probe "container:$c" "$t")
    echo "$c -> $t: $result"
    if [[ "$result" != "UNREACHABLE" ]]; then
      leaks=$((leaks + 1))
    fi
  done
done

if [[ "$leaks" -ne 0 ]]; then
  echo "FAIL: $leaks container-to-target paths are reachable. The testbed is not isolated."
  exit 1
fi
echo "PASS: no testbed container reached any target."
exit 0
