"""
gbn_sender.py — Go-Back-N sender.

Splits a file into 4096-byte chunks and transmits them over UDP using a
sliding window of size WINDOW_SIZE. On timeout, the entire unacknowledged
window is retransmitted (Go-Back-N semantics). Connects to 127.0.0.1:5001.

Usage: python gbn_sender.py <input_file>
Output: RESULT time=<s> throughput=<B/s> retransmissions=<n>
"""
import socket
import time
import sys
import os
from common import MAX_DATA, ACK_SIZE, make_packet, parse_ack

WINDOW_SIZE = 4
TIMEOUT = 0.05          # 50 ms — generous for loopback
HOST = '127.0.0.1'
PORT = 5001
MAX_TIMEOUTS = 30       # abort after 30 consecutive timeouts with no progress

def send_file(filepath):
    """
    Send a file using Go-Back-N over UDP.

    Returns (elapsed_seconds, total_retransmissions).
    Aborts early if MAX_TIMEOUTS consecutive timeouts occur with no progress.
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    chunks = [raw[i:i + MAX_DATA] for i in range(0, len(raw), MAX_DATA)] or [b'']
    n = len(chunks)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    base = 0
    nextseqnum = 0
    retransmissions = 0
    consecutive_timeouts = 0
    start_time = time.time()

    while base < n:
        # Fill the window with new packets
        while nextseqnum < base + WINDOW_SIZE and nextseqnum < n:
            is_eof = (nextseqnum == n - 1)
            pkt = make_packet(nextseqnum, chunks[nextseqnum], is_eof)
            sock.sendto(pkt, (HOST, PORT))
            nextseqnum += 1

        # Wait for one ACK
        try:
            raw_ack, _ = sock.recvfrom(ACK_SIZE + 4)
            ack_num = parse_ack(raw_ack)
            if base <= ack_num < n:
                base = ack_num + 1
                consecutive_timeouts = 0
        except socket.timeout:
            # Timer expired — Go Back N: retransmit entire window
            retransmissions += nextseqnum - base
            nextseqnum = base
            consecutive_timeouts += 1
            if consecutive_timeouts >= MAX_TIMEOUTS:
                print("ERROR: too many consecutive timeouts, aborting", file=sys.stderr)
                break

    elapsed = time.time() - start_time
    sock.close()
    return elapsed, retransmissions

if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'test.bin'
    elapsed, retrans = send_file(filepath)
    file_size = os.path.getsize(filepath)
    throughput = file_size / elapsed if elapsed > 0 else 0
    print(f"RESULT time={elapsed:.4f} throughput={throughput:.2f} retransmissions={retrans}")
