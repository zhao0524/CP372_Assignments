"""
saw_receiver.py — Stop-and-Wait receiver.

Binds to 127.0.0.1:5002 and accepts packets from saw_sender. Behaves
identically to gbn_receiver but on a separate port so both protocols can
run concurrently without conflict. Supports configurable packet loss
simulation.

Usage: python saw_receiver.py <output_file> [loss_rate]
"""
import socket
import sys
import random
from common import MAX_DATA, HEADER_SIZE, ACK_SIZE, parse_packet, make_ack

HOST = '127.0.0.1'
PORT = 5002

def receive_file(output_path, loss_rate=0.0):
    """
    Receive a file from saw_sender and write it to output_path.

    loss_rate: probability [0.0, 1.0] that any given incoming packet is dropped,
               simulating network packet loss.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))

    expected_seq = 0
    chunks = {}

    while True:
        raw, addr = sock.recvfrom(HEADER_SIZE + MAX_DATA + 4)

        # Simulate packet loss
        if random.random() < loss_rate:
            continue

        seq_num, data, is_eof = parse_packet(raw)

        if seq_num == expected_seq:
            chunks[seq_num] = data
            expected_seq += 1
            sock.sendto(make_ack(seq_num), addr)
            if is_eof:
                for _ in range(3):
                    sock.sendto(make_ack(seq_num), addr)
                break
        elif expected_seq > 0:
            sock.sendto(make_ack(expected_seq - 1), addr)

    sock.close()
    with open(output_path, 'wb') as f:
        for i in range(expected_seq):
            f.write(chunks[i])

if __name__ == '__main__':
    output_path = sys.argv[1] if len(sys.argv) > 1 else 'received.bin'
    loss_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    receive_file(output_path, loss_rate)
    print(f"Done: {output_path}")
