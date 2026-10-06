FROM python:3.12.11-slim-bookworm

# ADR-0008: tcpdump writes the run's raw pcaps; NFStream (ADR-0002) reads them afterwards.
# ADR-0009: one egress-only tcpdump sidecar per host; tcpslice merges their pcaps by timestamp.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tcpdump=4.99.3-1 tcpslice=1.5-1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir nfstream==6.6.0

COPY flows.py check_direction.py merge.sh /app/
WORKDIR /app
# Each capture-* service in docker-compose.yml sets its own tcpdump command (packet-buffered,
# -U, so each pcap is complete when tcpdump stops on SIGTERM).
CMD ["tcpdump", "--version"]
