"""
gbn_sender.py — Go-Back-N sender (synthetic payload version)

Generates a virtual file of size N MB and sends it using Go-Back-N over UDP.
Payload is generated on-the-fly per packet (no full buffering).

Usage: python gbn_sender.py <size_mb>
Output: RESULT time=<s> throughput=<B/s> retransmissions=<n>
"""

import socket
import time
import sys
import os

from common import MAX_DATA, ACK_SIZE, make_packet, parse_ack

WINDOW_SIZE = 4
TIMEOUT = 0.05
HOST = '127.0.0.1'
PORT = 5001
MAX_TIMEOUTS = 30


def generate_chunk(start_byte: int, length: int, total_size: int) -> bytes:
    """
    Deterministic synthetic payload generator.

    We generate bytes based on position so retransmissions match exactly.
    This avoids storing the full file.
    """
    end = min(start_byte + length, total_size)

    # simple deterministic pattern (fast + reproducible)
    # byte = (position % 256)
    return bytes((i % 256 for i in range(start_byte, end)))


def send_virtual_file(size_mb: float):
    total_size = int(size_mb * 1024 * 1024)
    n = (total_size + MAX_DATA - 1) // MAX_DATA

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    base = 0
    nextseqnum = 0
    retransmissions = 0
    consecutive_timeouts = 0

    start_time = time.time()

    while base < n:
        # Fill window
        while nextseqnum < base + WINDOW_SIZE and nextseqnum < n:
            start_byte = nextseqnum * MAX_DATA
            payload = generate_chunk(start_byte, MAX_DATA, total_size)

            is_eof = (nextseqnum == n - 1)
            pkt = make_packet(nextseqnum, payload, is_eof)

            sock.sendto(pkt, (HOST, PORT))
            nextseqnum += 1

        # Wait for ACK
        try:
            raw_ack, _ = sock.recvfrom(ACK_SIZE + 4)
            ack_num = parse_ack(raw_ack)

            if base <= ack_num < n:
                base = ack_num + 1
                consecutive_timeouts = 0

        except socket.timeout:
            # Go-Back-N retransmit window
            retransmissions += nextseqnum - base
            nextseqnum = base
            consecutive_timeouts += 1

            if consecutive_timeouts >= MAX_TIMEOUTS:
                print("ERROR: too many consecutive timeouts, aborting", file=sys.stderr)
                break

    elapsed = time.time() - start_time
    sock.close()
    return elapsed, retransmissions, total_size


if __name__ == '__main__':
    size_mb = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

    elapsed, retrans, total_size = send_virtual_file(size_mb)

    throughput = total_size / elapsed if elapsed > 0 else 0
    print(f"RESULT time={elapsed:.4f} throughput={throughput:.2f} retransmissions={retrans}")
