FROM python:3.12.11-slim-bookworm

# ADR-0008: tcpdump writes the run's raw pcap; NFStream (ADR-0002) reads it afterwards.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tcpdump=4.99.3-1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir nfstream==6.6.0

COPY flows.py check_direction.py /app/
WORKDIR /app
# Packet-buffered (-U) so the pcap is complete when tcpdump stops on SIGTERM.
CMD ["tcpdump", "-i", "eth0", "-s", "0", "-n", "-U", "-w", "/out/raw.pcap"]
