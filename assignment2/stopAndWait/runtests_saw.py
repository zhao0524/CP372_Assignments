import subprocess
import sys
import os
import time
import re

DIR = os.path.dirname(os.path.abspath(__file__))

FILE_SIZES  = ["0.01", "0.05", "0.1", "0.5", "1", "5", "10", "50", "100"]
LOSS_RATES  = ["0", "0.1", "0.2", "0.3"]
RUNS        = 5
RUN_TIMEOUT = 600   # seconds per individual run before giving up

for mb in FILE_SIZES:
    for loss in LOSS_RATES:
        times, throughputs, retranses = [], [], []

        for i in range(RUNS):

            recv = subprocess.Popen(
                [sys.executable, "receiver_stopwait.py", loss],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=DIR
            )
            time.sleep(0.3)  # give receiver time to bind

            try:
                send = subprocess.run(
                    [sys.executable, "sender_stopwait.py", "-q", mb],
                    capture_output=True,
                    text=True,
                    timeout=RUN_TIMEOUT,
                    cwd=DIR
                )
            except subprocess.TimeoutExpired:
                recv.kill()
                recv.communicate()
                continue

            recv.terminate()
            recv.communicate()
            time.sleep(0.3)  # let OS release port 5001 before next receiver starts
            m = re.search(r'RESULT time=(\S+) throughput=(\S+) retransmissions=(\d+)', send.stdout)
            if m:
                times.append(float(m.group(1)))
                throughputs.append(float(m.group(2)))
                retranses.append(int(m.group(3)))

        if times:
            avg_t  = sum(times)       / len(times)
            avg_tp = sum(throughputs) / len(throughputs)
            avg_r  = sum(retranses)   / len(retranses)
            print("SIZE: " + mb + "MB | " + "LOSS: " + loss + "% | AVG OF 5 RUNS: " + str(avg_t))
