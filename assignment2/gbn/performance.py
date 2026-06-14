"""
performance.py — Automated experiment runner for GBN vs Stop-and-Wait.

Runs every combination of protocol × file_size × loss_rate (5 trials each)
and prints averaged results as CSV to stdout. Progress is logged to stderr.

File sizes tested : 10KB, 50KB, 100KB, 500KB, 1MB, 5MB, 10MB, 50MB, 100MB
Loss rates tested : 0%, 10%, 20%, 30%
Protocols tested  : gbn, saw

Usage: python performance.py > results.csv
"""
import subprocess
import sys
import os
import time
import re

FILE_CONFIGS = [
    ('10KB',   10   * 1024),
    ('50KB',   50   * 1024),
    ('100KB',  100  * 1024),
    ('500KB',  500  * 1024),
    ('1MB',    1    * 1024 * 1024),
    ('5MB',    5    * 1024 * 1024),
    ('10MB',   10   * 1024 * 1024),
    ('50MB',   50   * 1024 * 1024),
    ('100MB',  100  * 1024 * 1024),
]
LOSS_RATES = [0.0, 0.1, 0.2, 0.3]
TESTS = 5
SENDER_TIMEOUT = 600   # seconds per test; large files at high loss can be slow

def gen_file(path, size):
    """Write `size` random bytes to `path`."""
    with open(path, 'wb') as f:
        f.write(os.urandom(size))

def run_one(protocol, filepath, loss_rate):
    """
    Run one sender/receiver pair and return (time_s, throughput_Bps, retransmissions).

    Spawns the receiver subprocess first, waits for it to bind, then runs the
    sender. Returns None on timeout or if the sender output cannot be parsed.
    """
    recv_script = 'gbn_receiver.py' if protocol == 'gbn' else 'saw_receiver.py'
    send_script = 'gbn_sender.py'   if protocol == 'gbn' else 'saw_sender.py'
    output = f'_recv_{protocol}.bin'

    recv = subprocess.Popen(
        [sys.executable, recv_script, output, str(loss_rate)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(0.3)   # give receiver time to bind its socket

    try:
        result = subprocess.run(
            [sys.executable, send_script, filepath],
            capture_output=True,
            text=True,
            timeout=SENDER_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        recv.kill()
        return None

    try:
        recv.wait(timeout=10)
    except subprocess.TimeoutExpired:
        recv.kill()

    m = re.search(r'time=(\S+) throughput=(\S+) retransmissions=(\d+)', result.stdout)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), int(m.group(3))

def main():
    os.makedirs('test_files', exist_ok=True)
    print("protocol,file_size,loss_pct,avg_time_s,avg_throughput_Bps,avg_retransmissions")

    for name, size in FILE_CONFIGS:
        fpath = f'test_files/{name}.bin'
        if not os.path.exists(fpath):
            print(f"# generating {name}...", file=sys.stderr)
            gen_file(fpath, size)

        for loss in LOSS_RATES:
            for proto in ['saw', 'gbn']:
                times, throughputs, retranses = [], [], []
                for run in range(TESTS):
                    print(f"# {proto} {name} loss={int(loss*100)}% run {run+1}/{TESTS}", file=sys.stderr)
                    r = run_one(proto, fpath, loss)
                    if r:
                        times.append(r[0])
                        throughputs.append(r[1])
                        retranses.append(r[2])

                if times:
                    avg_t  = sum(times)      / len(times)
                    avg_tp = sum(throughputs) / len(throughputs)
                    avg_r  = sum(retranses)   / len(retranses)
                    print(f"{proto},{name},{int(loss*100)},{avg_t:.4f},{avg_tp:.2f},{avg_r:.1f}")
                    sys.stdout.flush()

if __name__ == '__main__':
    main()
