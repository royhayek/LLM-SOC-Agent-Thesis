"""ADR-0002 check: NFStream's src_ip is the sender of a flow's first packet.

Writes a small test pcap with the standard library, reads it back with NFStream using the
sidecar's settings, and checks two TCP flows:
  A. a full handshake: the client sends the first packet (SYN);
  B. a capture that starts mid-connection: the server sends the first packet (no SYN).
Also checks that src2dst_syn_packets and src2dst_ack_packets are present.

Run inside the capture image:
  docker run --rm --entrypoint python thesis-testbed-capture:e1-16 check_direction.py
Exit 0 if every check holds, 1 otherwise.
"""

from __future__ import annotations

import socket
import struct
import sys
import tempfile
from pathlib import Path

from flows import ACCOUNTING_MODE, STATISTICAL_ANALYSIS
from nfstream import NFStreamer

SYN, ACK, PSH, FIN = 0x02, 0x10, 0x08, 0x01
MAC_A, MAC_B = b"\x02\x00\x00\x00\x00\x01", b"\x02\x00\x00\x00\x00\x02"


def _ip_checksum(header: bytes) -> int:
    total = sum(struct.unpack(f"!{len(header) // 2}H", header))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def _frame(src: str, dst: str, sport: int, dport: int, flags: int, payload: bytes = b"") -> bytes:
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, 5 << 4, flags, 65535, 0, 0) + payload
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp),
        0,
        0,
        64,
        6,
        0,
        socket.inet_aton(src),
        socket.inet_aton(dst),
    )
    ip = ip[:10] + struct.pack("!H", _ip_checksum(ip)) + ip[12:]
    src_mac, dst_mac = (MAC_A, MAC_B) if src.endswith(".1") else (MAC_B, MAC_A)
    return dst_mac + src_mac + b"\x08\x00" + ip + tcp


def _write_pcap(path: Path, frames: list[bytes]) -> None:
    with path.open("wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for i, frame in enumerate(frames):
            f.write(struct.pack("<IIII", 1_700_000_000, i * 1000, len(frame), len(frame)))
            f.write(frame)


def main() -> int:
    client, server = "10.0.0.1", "10.0.0.2"
    frames = [
        # A: handshake, client first.
        _frame(client, server, 40000, 1883, SYN),
        _frame(server, client, 1883, 40000, SYN | ACK),
        _frame(client, server, 40000, 1883, ACK),
        _frame(client, server, 40000, 1883, PSH | ACK, b"hello"),
        _frame(server, client, 1883, 40000, ACK),
        # B: capture starts mid-connection, server first.
        _frame(server, client, 1883, 40001, PSH | ACK, b"data"),
        _frame(client, server, 40001, 1883, ACK),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        pcap = Path(tmp) / "direction.pcap"
        _write_pcap(pcap, frames)
        flows = list(
            NFStreamer(
                source=str(pcap),
                statistical_analysis=STATISTICAL_ANALYSIS,
                accounting_mode=ACCOUNTING_MODE,
            )
        )

    by_port = {}
    for f in flows:
        by_port[f.src_port if f.src_ip == client else f.dst_port] = f
    checks = []
    a, b = by_port.get(40000), by_port.get(40001)
    checks.append(("two flows found", a is not None and b is not None))
    if a is not None and b is not None:
        checks.append(("A: src_ip is the client (first-packet sender)", a.src_ip == client))
        checks.append(("A: src2dst_syn_packets == 1", a.src2dst_syn_packets == 1))
        checks.append(("A: src2dst_ack_packets == 2", a.src2dst_ack_packets == 2))
        checks.append(("B: src_ip is the server (first-packet sender)", b.src_ip == server))
        checks.append(("B: src2dst_syn_packets == 0", b.src2dst_syn_packets == 0))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
