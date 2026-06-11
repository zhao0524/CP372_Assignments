import struct

MAX_DATA = 4096
# Header: seq_num (uint32=4B), data_len (uint16=2B), is_eof (uint8=1B) = 7B
HEADER_FMT = '!IHB'
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 7
ACK_FMT = '!I'
ACK_SIZE = struct.calcsize(ACK_FMT)         # 4

def make_packet(seq_num, data, is_eof=False):
    header = struct.pack(HEADER_FMT, seq_num, len(data), int(is_eof))
    return header + data

def parse_packet(raw):
    seq_num, data_len, is_eof = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])
    data = raw[HEADER_SIZE:HEADER_SIZE + data_len]
    return seq_num, data, bool(is_eof)

def make_ack(ack_num):
    return struct.pack(ACK_FMT, ack_num)

def parse_ack(raw):
    return struct.unpack(ACK_FMT, raw[:ACK_SIZE])[0]
