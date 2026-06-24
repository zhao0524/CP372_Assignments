"""
sender_stopwait.py - Stop-and-Wait sender.

Sends a file one 4096-byte chunk at a time over UDP, waiting for each ACK
before transmitting the next packet (window size = 1). Connects to
127.0.0.1:5001. Retransmits up to MAX_RETRIES times per packet on timeout
or stale ACK.

Usage: python sender_stopwait.py [-q] <size_mb>
  -q   Quiet mode: suppress per-packet output, only print the RESULT line.
Output: RESULT time=<s> throughput=<B/s> retransmissions=<n>
"""
import socket
import struct
import time
import sys
import hashlib

# config
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001
PACKET_SIZE  = 512          # bytes per data chunk
TIMEOUT      = 2.0          # seconds before retransmit
MAX_RETRIES  = 10

# quiet flag - set before any function runs
QUIET = '-q' in sys.argv

# packet types (gotta match receiver)
TYPE_INIT   = 0   # "about to upload a file"
TYPE_DATA   = 1   # data chunk
TYPE_FIN    = 2   # end of file
TYPE_ACK    = 3   # acknowledgement (receiver -> sender)

# packet format (header = 7 bytes)
# | type (1B) | seq_num (2B) | data_len (2B) | checksum (2B) | data (variable) |
HEADER_FMT  = '!BHHH'
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 7 bytes (hopefully)

def checksum(data: bytes) -> int:
    """Simple 16-bit checksum."""
    return int(hashlib.md5(data).hexdigest(), 16) & 0xFFFF

def make_packet(pkt_type: int, seq: int, data: bytes = b'') -> bytes:
    ck = checksum(data)
    header = struct.pack(HEADER_FMT, pkt_type, seq, len(data), ck)
    return header + data

def parse_ack(raw: bytes):
    """Returns (ack_type, ack_seq) or None on error."""
    if len(raw) < HEADER_SIZE:
        return None
    pkt_type, seq, _, _ = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])
    return pkt_type, seq

def send_with_retry(sock, packet: bytes, expected_seq: int, label: str):
    """
    Send packet and retry until ACK received or MAX_RETRIES exhausted.
    Returns (success: bool, retransmissions: int).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        sock.sendto(packet, (SERVER_HOST, SERVER_PORT))
        if not QUIET:
            print(f"  [TX] {label} seq={expected_seq}  (attempt {attempt})")
        sock.settimeout(TIMEOUT)

        try:
            raw, _ = sock.recvfrom(HEADER_SIZE + 16)
            result = parse_ack(raw)
            if result and result[0] == TYPE_ACK and result[1] == expected_seq:
                if not QUIET:
                    print(f"  [ACK] seq={expected_seq} received OK")
                return True, attempt - 1
            else:
                if not QUIET:
                    print(f"  [WARN] Unexpected ACK {result}, retrying...")
        except socket.timeout:
            if not QUIET:
                print(f"  [TIMEOUT] seq={expected_seq}, retransmitting...")

    if not QUIET:
        print(f"  [FAIL] Max retries reached for seq={expected_seq}")
    return False, MAX_RETRIES

def transfer_data(size_mb: float):
    """
    Send size_mb megabytes of dummy data using Stop-and-Wait.
    Returns (elapsed_seconds, total_retransmissions), or None on INIT failure.
    """
    total_bytes = int(size_mb * 1024 * 1024)
    file_data = b'X' * total_bytes

    if not QUIET:
        print(f"[INFO] Generated {total_bytes:,} bytes ({size_mb} MB) of dummy data")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total_retrans = 0

    # INIT packet
    if not QUIET:
        print("\n[PHASE 1] Sending INIT ...")
    init_data = f"dummy_{size_mb}MB.bin".encode("utf-8")
    pkt = make_packet(TYPE_INIT, 0, init_data)

    start = time.time()
    ok, r = send_with_retry(sock, pkt, 0, "INIT")
    total_retrans += r
    if not ok:
        if not QUIET:
            print("[ERROR] INIT failed. Aborting.")
        sock.close()
        return None

    # DATA packets
    if not QUIET:
        print("\n[PHASE 2] Sending DATA ...")

    chunks = [file_data[i:i + PACKET_SIZE] for i in range(0, len(file_data), PACKET_SIZE)]

    seq = 1
    for i, chunk in enumerate(chunks):
        pkt = make_packet(TYPE_DATA, seq, chunk)
        ok, r = send_with_retry(sock, pkt, seq, f"DATA chunk {i+1}/{len(chunks)}")
        total_retrans += r
        if not ok:
            if not QUIET:
                print(f"[ERROR] Failed at chunk {i+1}. Aborting.")
            sock.close()
            return None
        seq = 1 - seq  # alternating bit

    # FIN packet
    if not QUIET:
        print("\n[PHASE 3] Sending FIN ...")
    pkt = make_packet(TYPE_FIN, seq, b'')
    ok, r = send_with_retry(sock, pkt, seq, "FIN")
    total_retrans += r
    if not QUIET:
        if ok:
            print("\n[DONE] Transfer complete OK")
        else:
            print("[ERROR] FIN not ACK'd.")

    sock.close()
    return time.time() - start, total_retrans

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '-q']

    if len(args) != 1:
        print(f"Usage: python {sys.argv[0]} [-q] <size_mb>")
        sys.exit(1)

    size_mb = float(args[0])
    result = transfer_data(size_mb)
    if result:
        elapsed, retrans = result
        throughput = (size_mb * 1024 * 1024) / elapsed if elapsed > 0 else 0
        print(f"RESULT time={elapsed:.4f} throughput={throughput:.2f} retransmissions={retrans}")
