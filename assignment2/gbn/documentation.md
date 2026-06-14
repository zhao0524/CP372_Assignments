# CP372 Assignment 2 — GBN & Stop-and-Wait Documentation

## Overview

This module implements two sliding-window reliable transfer protocols over UDP:

- **Go-Back-N (GBN)** — sender maintains a window of up to `WINDOW_SIZE` unacknowledged packets. On any timeout, the entire window is retransmitted from the last unacknowledged packet.
- **Stop-and-Wait (S&W)** — a degenerate window of size 1; the sender transmits one packet and waits for its ACK before proceeding.

Both protocols use a shared binary packet format defined in `common.py`, simulate packet loss at the receiver, and report throughput + retransmission counts so performance can be compared.

---

## File Reference

### `common.py` — Shared Packet Format

Defines the binary wire format used by all senders and receivers.

**Packet layout:**

```
[ seq_num: 4B uint32 ][ data_len: 2B uint16 ][ is_eof: 1B uint8 ][ data: 0–4096B ]
 ←──────────────────────── 7-byte header ──────────────────────────→
```

**ACK layout:**

```
[ ack_num: 4B uint32 ]
```

**Constants:**

| Name | Value | Purpose |
|------|-------|---------|
| `MAX_DATA` | 4096 | Maximum payload bytes per packet |
| `HEADER_FMT` | `'!IHB'` | Big-endian struct format for the 7-byte header |
| `HEADER_SIZE` | 7 | Computed from `HEADER_FMT` |
| `ACK_FMT` | `'!I'` | Big-endian struct format for a 4-byte ACK |
| `ACK_SIZE` | 4 | Computed from `ACK_FMT` |

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `make_packet` | `(seq_num, data, is_eof=False) → bytes` | Serializes a data packet. Sets `is_eof=True` on the last chunk to signal end-of-file. |
| `parse_packet` | `(raw) → (seq_num, data, is_eof)` | Deserializes a received packet into its fields. |
| `make_ack` | `(ack_num) → bytes` | Serializes a 4-byte cumulative ACK. |
| `parse_ack` | `(raw) → ack_num` | Deserializes a received ACK. |

---

### `gbn_sender.py` — Go-Back-N Sender

Reads a file, splits it into 4096-byte chunks, and sends them using the Go-Back-N protocol over UDP to `127.0.0.1:5001`.

**Configuration constants:**

| Constant | Default | Description |
|----------|---------|-------------|
| `WINDOW_SIZE` | 4 | Number of unACKed packets in flight |
| `TIMEOUT` | 0.05 s | Socket receive timeout before retransmit |
| `HOST` | `'127.0.0.1'` | Receiver address |
| `PORT` | 5001 | Receiver port |
| `MAX_TIMEOUTS` | 30 | Consecutive timeouts before aborting |

**Function: `send_file(filepath)`**

Returns `(elapsed_seconds, retransmissions)`.

Algorithm:
1. Read the entire file into memory and split into chunks.
2. Maintain two pointers: `base` (oldest unACKed seq) and `nextseqnum` (next to send).
3. Fill the window by sending packets up to `base + WINDOW_SIZE`.
4. Block on `recvfrom` waiting for an ACK.
   - Valid ACK: advance `base` to `ack_num + 1`, reset timeout counter.
   - Timeout: reset `nextseqnum = base` (retransmit entire window), increment timeout counter.
5. If `consecutive_timeouts >= MAX_TIMEOUTS`, abort with an error.

**Usage:**
```bash
python gbn_sender.py <input_file>
# Example:
python gbn_sender.py myfile.txt
```

**Output:**
```
RESULT time=0.0312 throughput=3201024.50 retransmissions=7
```

---

### `gbn_receiver.py` — Go-Back-N Receiver

Listens on `127.0.0.1:5001`, accepts packets from the GBN sender, and writes the reassembled file to disk.

**Configuration constants:**

| Constant | Default | Description |
|----------|---------|-------------|
| `HOST` | `'127.0.0.1'` | Address to bind |
| `PORT` | 5001 | Port to bind |

**Function: `receive_file(output_path, loss_rate=0.0)`**

Receives and reassembles chunks, then writes them in order to `output_path`.

Algorithm (GBN receiver — cumulative ACK, in-order delivery only):
1. Bind the UDP socket.
2. For each incoming packet, optionally discard it with probability `loss_rate` to simulate network loss.
3. If the packet matches `expected_seq`, store the chunk and ACK it, then increment `expected_seq`.
4. If the packet is out of order and at least one packet was already received, re-ACK the last successfully received sequence number (`expected_seq - 1`). This triggers a Go-Back-N retransmission at the sender.
5. On EOF packet, send the final ACK three extra times to survive ACK loss, then stop.
6. Write all chunks in sequence order to the output file.

**Usage:**
```bash
python gbn_receiver.py <output_file> [loss_rate]
# Example (20% loss):
python gbn_receiver.py received.bin 0.2
```

---

### `saw_sender.py` — Stop-and-Wait Sender

Identical in structure to `gbn_sender.py` but uses a window of 1 (sends one packet, then blocks until its ACK is received). Runs on port `5002`.

**Configuration constants:**

| Constant | Default | Description |
|----------|---------|-------------|
| `TIMEOUT` | 0.05 s | Socket receive timeout |
| `HOST` | `'127.0.0.1'` | Receiver address |
| `PORT` | 5002 | Receiver port |
| `MAX_RETRIES` | 30 | Per-packet retransmit limit |

**Function: `send_file(filepath)`**

Returns `(elapsed_seconds, retransmissions)`.

Algorithm:
1. Split the file into chunks.
2. For each chunk: send the packet and wait for the matching ACK.
   - Correct ACK: advance to the next chunk.
   - Stale ACK or timeout: retransmit the same packet, increment `retransmissions`.
3. After `MAX_RETRIES` failed attempts on a single packet, move on (data loss).

**Usage:**
```bash
python saw_sender.py <input_file>
```

---

### `saw_receiver.py` — Stop-and-Wait Receiver

Listens on `127.0.0.1:5002`. Functionally identical to `gbn_receiver.py` — since S&W sends one packet at a time, out-of-order delivery cannot occur in practice, but the same GBN-receiver logic handles it gracefully if it does.

**Usage:**
```bash
python saw_receiver.py <output_file> [loss_rate]
```

---

### `performance.py` — Automated Experiment Runner

Runs a full cross-product of protocol × file size × loss rate, averaging 5 trials each, and prints a CSV to stdout.

**Test matrix:**

| Dimension | Values |
|-----------|--------|
| Protocols | `gbn`, `saw` |
| File sizes | 10KB, 50KB, 100KB, 500KB, 1MB, 5MB, 10MB, 50MB, 100MB |
| Loss rates | 0%, 10%, 20%, 30% |
| Runs per cell | 5 |

**How it works:**

1. Generates binary test files of random bytes in `test_files/` (skips if already present).
2. For each combination, spawns the receiver as a subprocess, waits 0.3 s for it to bind, then runs the sender.
3. Parses the `RESULT` line from sender stdout to extract time, throughput, and retransmissions.
4. Averages results across 5 runs and prints one CSV row per cell.

**CSV output format:**
```
protocol,file_size,loss_pct,avg_time_s,avg_throughput_Bps,avg_retransmissions
saw,10KB,0,0.0021,4876190.48,0.0
gbn,10KB,0,0.0008,12800000.00,0.0
```

**Usage:**
```bash
python performance.py > results.csv
# Progress is printed to stderr so it doesn't pollute the CSV:
python performance.py > results.csv 2>progress.log
```

> **Warning:** 50MB and 100MB tests at 30% loss with S&W can take many minutes. The per-test timeout is 600 seconds.

---

## Protocol Comparison

| Property | Go-Back-N | Stop-and-Wait |
|----------|-----------|---------------|
| Window size | 4 | 1 |
| Port | 5001 | 5002 |
| On timeout | Retransmit all `WINDOW_SIZE` packets from `base` | Retransmit single packet |
| Throughput at 0% loss | ~4× higher than S&W | Baseline |
| Throughput at high loss | Degrades due to bulk retransmission | Degrades but wastes less bandwidth |

---

## Quick Start

```bash
# Terminal 1 — start receiver
python gbn_receiver.py received.bin 0.0

# Terminal 2 — send file
python gbn_sender.py myfile.txt

# Run performance experiments
python performance.py > results.csv
```
