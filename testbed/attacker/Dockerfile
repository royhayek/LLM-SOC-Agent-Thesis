FROM debian:bookworm-slim

# Attacker host for the external-origin families (ADR-0003): port scan (F3, nmap), SSH
# credential guessing (F4, hydra), SYN flood (F6, hping3), and botnet replay (F5, tcpreplay).
# Versions pinned to the Debian bookworm packages ADR-0003 names. These are standard tools;
# no custom exploit code (record §5). The container runs idle on the isolated testbed network
# and is driven per episode with `docker exec`; it has no route off the internal network.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nmap=7.93+dfsg1-1 \
        hydra=9.4-1 \
        hping3=3.a2.ds2-10 \
        tcpreplay=4.4.3-1 \
        procps=2:4.0.2-3 \
    && rm -rf /var/lib/apt/lists/*

# Idle until an episode drives it, so it is present and isolated when the E1-01 gate runs.
CMD ["sleep", "infinity"]
