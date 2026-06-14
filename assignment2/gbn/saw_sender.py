"""
saw_sender.py — Stop-and-Wait sender.

Sends a file one 4096-byte chunk at a time over UDP, waiting for each ACK
before transmitting the next packet (window size = 1). Connects to
127.0.0.1:5002. Retransmits up to MAX_RETRIES times per packet on timeout
or stale ACK.

Usage: python saw_sender.py <input_file>
Output: RESULT time=<s> throughput=<B/s> retransmissions=<n>
"""
import socket
import time
import sys
import os
from common import MAX_DATA, ACK_SIZE, make_packet, parse_ack

TIMEOUT = 0.05          # 50 ms — generous for loopback
HOST = '127.0.0.1'
PORT = 5002
MAX_RETRIES = 30

def send_file(filepath):
    """
    Send a file using Stop-and-Wait over UDP.

    Returns (elapsed_seconds, total_retransmissions).
    Moves on after MAX_RETRIES failed attempts on a single packet.
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    chunks = [raw[i:i + MAX_DATA] for i in range(0, len(raw), MAX_DATA)] or [b'']
    n = len(chunks)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    retransmissions = 0
    start_time = time.time()

    for i, chunk in enumerate(chunks):
        is_eof = (i == n - 1)
        pkt = make_packet(i, chunk, is_eof)
        retries = 0
        while retries < MAX_RETRIES:
            sock.sendto(pkt, (HOST, PORT))
            try:
                raw_ack, _ = sock.recvfrom(ACK_SIZE + 4)
                if parse_ack(raw_ack) == i:
                    break               # correct ACK received, move to next packet
                retransmissions += 1   # stale ACK, retransmit
            except socket.timeout:
                retransmissions += 1
            retries += 1

    elapsed = time.time() - start_time
    sock.close()
    return elapsed, retransmissions

if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'test.bin'
    elapsed, retrans = send_file(filepath)
    file_size = os.path.getsize(filepath)
    throughput = file_size / elapsed if elapsed > 0 else 0
    print(f"RESULT time={elapsed:.4f} throughput={throughput:.2f} retransmissions={retrans}")
