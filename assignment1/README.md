# Stop-and-Wait Protocol — README

A Python implementation of the **Stop-and-Wait** reliable data transfer protocol over UDP, with simulated packet loss for testing purposes.

---

## Files

| File | Role |
|------|------|
| `sender_stopwait.py` | Reads or generates a file, then transfers it packet-by-packet |
| `receiver_stopwait.py` | Listens for packets, reassembles the file, and ACKs each one |

---

## How to Run

Open **two terminals** in the same directory.

### Terminal 1 — Start the Receiver

```bash
# 0% packet loss (default)
python receiver_stopwait.py

# With simulated packet loss (Part B)
python receiver_stopwait.py 0.1   # 10%
python receiver_stopwait.py 0.2   # 20%
python receiver_stopwait.py 0.3   # 30%
```

The receiver binds to `0.0.0.0:5001` and waits. Received files are saved to `./received_files/`.

### Terminal 2 — Start the Sender

```bash
# Auto-generate random content
python sender_stopwait.py

# Transfer a specific file
python sender_stopwait.py myfile.txt
```

> **Important:** Always start the receiver before the sender.

---

## Packet Structure

Every packet (both data and ACK) shares the same 7-byte header:

```
+--------+---------+----------+-----------+-------------------+
| type   | seq_num | data_len | checksum  | data (payload)    |
| 1 byte | 2 bytes | 2 bytes  | 2 bytes   | 0–512 bytes       |
+--------+---------+----------+-----------+-------------------+
```

| Field | Description |
|-------|-------------|
| `type` | `0=INIT`, `1=DATA`, `2=FIN`, `3=ACK` |
| `seq_num` | Alternating-bit sequence number (0 or 1) |
| `data_len` | Number of bytes in the payload |
| `checksum` | 16-bit MD5-based integrity check |

---

## Protocol Flow

The transfer happens in three phases:

```
Sender                              Receiver
  |                                    |
  |-- INIT (seq=0, filename) -------->  |   Phase 1: notify receiver a file is coming
  |<--------- ACK (seq=0) ----------- |
  |                                    |
  |-- DATA (seq=1, chunk 1) -------->  |   Phase 2: send file data one packet at a time
  |<--------- ACK (seq=1) ----------- |
  |-- DATA (seq=0, chunk 2) -------->  |
  |<--------- ACK (seq=0) ----------- |
  |           ... (repeats) ...        |
  |                                    |
  |-- FIN  (seq=N) ----------------->  |   Phase 3: notify receiver transfer is done
  |<--------- ACK (seq=N) ----------- |
```

**Key behaviours:**

- The sender transmits exactly **one packet at a time** and waits for an ACK before sending the next.
- If no ACK arrives within **2 seconds**, the sender retransmits the same packet (up to 10 retries).
- Sequence numbers alternate between **0 and 1** (alternating-bit protocol).
- The receiver only accepts a packet if its sequence number matches the expected value; out-of-order packets are silently discarded.
- Duplicate packets (retransmissions the receiver already saw) are re-ACK'd so the sender can move forward.
- A 16-bit checksum on every packet detects corruption; corrupted packets are dropped without an ACK.

---

## Receiver State Machine

The receiver operates in two states:

```
         INIT packet
  IDLE ───────────────► RECEIVING
                             │
                     DATA packets (writes chunks to file)
                             │
                        FIN packet
                             │
  IDLE ◄───────────────────── (file closed and saved)
```

| State | What the receiver does |
|-------|------------------------|
| `IDLE` | Waits for an INIT packet to start a new transfer |
| `RECEIVING` | Accepts DATA packets in order; writes each chunk to the output file |
| *(transition)* | On FIN, closes the file and returns to `IDLE` |

---

## Part B — Simulated Packet Loss

The receiver randomly drops incoming packets before processing them:

```python
if random.random() < LOSS_RATE:
    drop packet   # no ACK is sent → sender times out and retransmits
```

Because the sender retransmits on timeout, the file always arrives intact — it just takes more round trips at higher loss rates.

### Expected behaviour by loss rate

| Loss Rate | Behaviour |
|-----------|-----------|
| 0% | Clean transfer, no retransmissions |
| 10% | Occasional `[TIMEOUT]` / `[DROP]` lines, slight slowdown |
| 20% | More retransmissions, noticeably slower |
| 30% | Frequent retransmissions, but transfer still completes |

---

## Configuration

All tuneable constants are at the top of each file:

| Constant | File | Default | Description |
|----------|------|---------|-------------|
| `SERVER_HOST` | sender | `127.0.0.1` | Receiver IP address |
| `SERVER_PORT` | sender | `5001` | Receiver UDP port |
| `PACKET_SIZE` | sender | `512` | Bytes per data chunk |
| `TIMEOUT` | sender | `2.0` s | Retransmit timeout |
| `MAX_RETRIES` | sender | `10` | Max retransmit attempts |
| `LISTEN_PORT` | receiver | `5001` | Port to bind |
| `OUTPUT_DIR` | receiver | `./received_files` | Where to save files |
| `LOSS_RATE` | receiver | `0.0` | Packet drop probability (0.0–1.0) |

---

## Sample Output

**Receiver (20% loss):**
```
[INFO] Receiver listening on 0.0.0.0:5001
[INFO] Loss rate = 20%

[INIT] New transfer: 'generated_content.txt' → './received_files/generated_content.txt'
  [DROP] Simulated packet loss
  [DATA] seq=1 (512 bytes) saved
  [DROP] Simulated packet loss
  [DATA] seq=0 (512 bytes) saved
  ...
[FIN] Transfer complete – file saved
```

**Sender (20% loss on receiver side):**
```
[PHASE 1] Sending INIT …
  [TX] INIT seq=0  (attempt 1)
  [ACK] seq=0 received ✓

[PHASE 2] Sending DATA …
  [TX] DATA chunk 1/3 seq=1  (attempt 1)
  [TIMEOUT] seq=1, retransmitting…
  [TX] DATA chunk 1/3 seq=1  (attempt 2)
  [ACK] seq=1 received ✓
  ...

[DONE] File transfer complete ✓
```

---

## Requirements

- Python 3.6+
- No external libraries — uses only the standard library (`socket`, `struct`, `hashlib`, `random`, `os`)
