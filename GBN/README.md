# CP372 - Assignment 1: Go-Back-N Protocol (Part C & D)

UDP-based implementation of Go-Back-N (GBN) and Stop-and-Wait (S&W) with packet loss simulation and automated performance comparison.

## Requirements

- Python 3.x
- Standard library only (`socket`, `struct`, `random`, `subprocess`) — no external packages needed

## Project Structure

```
GBN/
├── common.py        — shared packet format (used by all other files)
├── gbn_sender.py    — Go-Back-N sender        (port 5001)
├── gbn_receiver.py  — Go-Back-N receiver      (port 5001)
├── saw_sender.py    — Stop-and-Wait sender     (port 5002)
├── saw_receiver.py  — Stop-and-Wait receiver   (port 5002)
└── performance.py   — automated experiment runner (outputs CSV)
```

---

## How the Packet Format Works (`common.py`)

Every packet sent over UDP has this layout:

```
[ seq_num: 4B ][ data_len: 2B ][ is_eof: 1B ][ data: up to 4096B ]
 ←────────── 7-byte header ──────────────────→
```

ACK packets are just 4 bytes: `[ ack_num: 4B ]`

All other files import `make_packet`, `parse_packet`, `make_ack`, `parse_ack` from here.

---

## Running Go-Back-N

Open **two terminals** inside the `GBN/` folder.

**Terminal 1 — start the receiver first:**

```bash
python gbn_receiver.py <output_file> <loss_rate>
```

**Terminal 2 — run the sender:**

```bash
python gbn_sender.py <input_file>
```

**Example (0% loss):**
```bash
# Terminal 1
python gbn_receiver.py received.bin 0.0

# Terminal 2
python gbn_sender.py myfile.txt
```

**Example (20% loss):**
```bash
# Terminal 1
python gbn_receiver.py received.bin 0.2

# Terminal 2
python gbn_sender.py myfile.txt
```

Sender output:
```
RESULT time=0.0312 throughput=3201024.50 retransmissions=7
```

---

## Running Stop-and-Wait

Same as GBN but use the `saw_` scripts (they run on port 5002):

```bash
# Terminal 1
python saw_receiver.py received.bin 0.2

# Terminal 2
python saw_sender.py myfile.txt
```

---

## Loss Rates

Both receivers accept a loss rate as the second argument:

| Value | Meaning |
|-------|---------|
| `0.0` | 0% loss — no packets dropped |
| `0.1` | 10% loss |
| `0.2` | 20% loss |
| `0.3` | 30% loss |

Loss is simulated at the receiver: each arriving packet is randomly discarded with the given probability.

---

## Running Performance Experiments (`performance.py`)

Runs all combinations automatically and outputs a CSV:

```bash
cd GBN
python performance.py > results.csv
```

Tests every combination of:
- **Protocols:** Stop-and-Wait, Go-Back-N
- **File sizes:** 10KB, 50KB, 100KB, 500KB, 1MB, 5MB, 10MB, 50MB, 100MB
- **Loss rates:** 0%, 10%, 20%, 30%
- **Runs:** 5 per combination

Test files are generated automatically in `GBN/test_files/`.

**CSV output format:**
```
protocol,file_size,loss_pct,avg_time_s,avg_throughput_Bps,avg_retransmissions
saw,10KB,0,0.0021,4876190.48,0.0
gbn,10KB,0,0.0008,12800000.00,0.0
saw,10KB,10,0.0187,548123.22,24.4
gbn,10KB,10,0.0051,2011764.71,6.2
...
```

> **Note:** 50MB and 100MB tests at 30% loss with Stop-and-Wait can take a long time. Progress is printed to stderr so you can monitor it.

---

## Protocol Settings

| Setting | GBN | S&W |
|---------|-----|-----|
| Window size | 4 | 1 |
| Timeout | 50 ms | 50 ms |
| Port | 5001 | 5002 |
| Chunk size | 4096 bytes | 4096 bytes |

To change the window size, edit `WINDOW_SIZE` in `gbn_sender.py`.
