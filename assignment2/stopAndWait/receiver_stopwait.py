import socket
import struct
import hashlib
import random
import os
import sys

# Config 
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 5001
OUTPUT_DIR  = './received_files'

# part b (configurable loss rate) (py receiver_stopwait.py 0.2)
LOSS_RATE   = 0.0   # 0%, 10%, 20%, 30% -> 0.0, 0.1, 0.2, 0.3

# packet types (must match sender file)
TYPE_INIT   = 0
TYPE_DATA   = 1
TYPE_FIN    = 2
TYPE_ACK    = 3

HEADER_FMT  = '!BHHH'
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 7 bytes

# helpers
def checksum(data: bytes) -> int:
    return int(hashlib.md5(data).hexdigest(), 16) & 0xFFFF

def parse_packet(raw: bytes):
    """Return (pkt_type, seq, data) or None if malformed / bad checksum."""
    if len(raw) < HEADER_SIZE:
        return None
    pkt_type, seq, data_len, recv_ck = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])
    data = raw[HEADER_SIZE:HEADER_SIZE + data_len]
    if len(data) != data_len:
        return None
    if checksum(data) != recv_ck:
        print(f"  [CHECKSUM ERROR] seq={seq} - packet discarded")
        return None
    return pkt_type, seq, data

def make_ack(seq: int) -> bytes:
    header = struct.pack(HEADER_FMT, TYPE_ACK, seq, 0, 0)
    return header

def should_drop() -> bool:
    """Part B: simulate random packet loss."""
    if LOSS_RATE > 0 and random.random() < LOSS_RATE:
        return True
    return False

# receiver state machine 
def run_receiver():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    print(f"[INFO] Receiver listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"[INFO] Loss rate = {LOSS_RATE*100:.0f}%")
    print(f"[INFO] Output directory: {OUTPUT_DIR}/\n")

    file_handle  = None
    filename     = None
    expected_seq = 0          # alternating-bit expected seq
    state        = 'IDLE'     # IDLE -> RECEIVING -> DONE
    last_pkt_type = None
    last_seq      = None

    while True:
        raw, addr = sock.recvfrom(65535)

        # part B: random drop
        if should_drop():
            print(f"  [DROP] Simulated packet loss from {addr}")
            continue

        result = parse_packet(raw)
        if result is None:
            print(f"  [SKIP] Malformed packet from {addr}")
            continue

        pkt_type, seq, data = result

        # duplicate / out-of-order detection 
        # Re-ACK the last packet if we receive a retransmission of it
        if pkt_type == last_pkt_type and seq == last_seq and pkt_type != TYPE_INIT:
            print(f"  [DUP] Duplicate pkt type={pkt_type} seq={seq} - re-ACKing")
            sock.sendto(make_ack(seq), addr)
            continue

        # INIT 
        if pkt_type == TYPE_INIT:
            if seq != 0:
                print(f"  [WARN] INIT with unexpected seq={seq}, ignoring")
                continue
            filename = data.decode('utf-8', errors='replace')
            filepath = os.path.join(OUTPUT_DIR, os.path.basename(filename))
            file_handle = open(filepath, 'wb')
            expected_seq = 1    # first DATA uses seq=1 (alternating from INIT seq=0)
            state = 'RECEIVING'
            last_pkt_type, last_seq = TYPE_INIT, 0
            print(f"[INIT] New transfer: '{filename}' -> '{filepath}'")
            sock.sendto(make_ack(0), addr)

        # DATA 
        elif pkt_type == TYPE_DATA:
            if state != 'RECEIVING':
                print(f"  [WARN] DATA received outside RECEIVING state, ignoring")
                continue
            if seq != expected_seq:
                print(f"  [OUT-OF-ORDER] Expected seq={expected_seq}, got seq={seq} - discarding")
                # Do NOT ACK - sender will timeout and retransmit
                continue
            file_handle.write(data)
            print(f"  [DATA] seq={seq} ({len(data)} bytes) saved")
            last_pkt_type, last_seq = TYPE_DATA, seq
            expected_seq = 1 - expected_seq   # toggle
            sock.sendto(make_ack(seq), addr)

        # FIN 
        elif pkt_type == TYPE_FIN:
            if state != 'RECEIVING':
                print(f"  [WARN] FIN outside RECEIVING state, ignoring")
                continue
            if file_handle:
                file_handle.close()
                file_handle = None
            state = 'IDLE'
            last_pkt_type, last_seq = TYPE_FIN, seq
            print(f"[FIN] Transfer complete - file saved as '{filepath}'")
            sock.sendto(make_ack(seq), addr)
            print(f"\n[INFO] Ready for next transfer.\n")

        else:
            print(f"  [UNKNOWN] pkt_type={pkt_type} from {addr}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            LOSS_RATE = float(sys.argv[1])
            if not 0.0 <= LOSS_RATE <= 1.0:
                raise ValueError
        except ValueError:
            print("Usage: python receiver_stopwait.py [loss_rate]")
            print("  loss_rate must be a float between 0.0 and 1.0")
            sys.exit(1)
    run_receiver()
