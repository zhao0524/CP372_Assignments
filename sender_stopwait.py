import socket
import struct
import time
import random
import hashlib

# config 
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001
PACKET_SIZE  = 512          # bytes per data chunk
TIMEOUT      = 2.0          # seconds before retransmit
MAX_RETRIES  = 10

# packet types (gotta match receiver)
TYPE_INIT   = 0   # "about to upload a file"
TYPE_DATA   = 1   # data chunk
TYPE_FIN    = 2   # end of file
TYPE_ACK    = 3   # acknowledgement (receiver → sender)

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

def send_with_retry(sock, packet: bytes, expected_seq: int, label: str) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        sock.sendto(packet, (SERVER_HOST, SERVER_PORT))
        print(f"  [TX] {label} seq={expected_seq}  (attempt {attempt})")
        sock.settimeout(TIMEOUT)
        try:
            raw, _ = sock.recvfrom(HEADER_SIZE + 16)
            result = parse_ack(raw)
            if result and result[0] == TYPE_ACK and result[1] == expected_seq:
                print(f"  [ACK] seq={expected_seq} received ✓")
                return True
            else:
                print(f"  [WARN] Unexpected ACK {result}, retrying…")
        except socket.timeout:
            print(f"  [TIMEOUT] seq={expected_seq}, retransmitting…")
    print(f"  [FAIL] Max retries reached for seq={expected_seq}")
    return False

def transfer_file(filename: str = None):
    # generate or read content
    if filename:
        with open(filename, 'rb') as f:
            file_data = f.read()
        print(f"[INFO] Reading '{filename}' ({len(file_data)} bytes)")
    else:
        # generate 200 randomly ordered words for content
        words = ["network", "stop-and-wait", "protocol", "packet", "ACK",
                 "timeout", "retransmit", "sequence", "reliable", "UDP"]
        content = " ".join(random.choices(words, k=200)) + "\n"
        file_data = content.encode('utf-8')
        filename = "generated_content.txt"
        print(f"[INFO] Generated {len(file_data)}-byte payload → '{filename}'")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # INIT packet 
    print("\n[PHASE 1] Sending INIT …")
    init_data = filename.encode('utf-8')
    pkt = make_packet(TYPE_INIT, 0, init_data)
    if not send_with_retry(sock, pkt, 0, "INIT"):
        print("[ERROR] INIT failed. Aborting.")
        sock.close()
        return

    # DATA packets 
    print("\n[PHASE 2] Sending DATA …")
    chunks = [file_data[i:i + PACKET_SIZE]
              for i in range(0, len(file_data), PACKET_SIZE)]
    seq = 1
    for i, chunk in enumerate(chunks):
        pkt = make_packet(TYPE_DATA, seq, chunk)
        label = f"DATA chunk {i+1}/{len(chunks)}"
        if not send_with_retry(sock, pkt, seq, label):
            print(f"[ERROR] Failed at chunk {i+1}. Aborting.")
            sock.close()
            return
        seq = 1 - seq   # alternating bit: 0 ↔ 1

    # FIN packet
    print("\n[PHASE 3] Sending FIN …")
    pkt = make_packet(TYPE_FIN, seq, b'')
    if not send_with_retry(sock, pkt, seq, "FIN"):
        print("[ERROR] FIN not ACK'd.")
    else:
        print("\n[DONE] File transfer complete ✓")

    sock.close()

if __name__ == '__main__':
    import sys
    fname = sys.argv[1] if len(sys.argv) > 1 else None
    transfer_file(fname)
