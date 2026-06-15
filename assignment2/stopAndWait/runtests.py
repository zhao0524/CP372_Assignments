import subprocess
import sys
import time

for mb in ["0.01", "0.05", "0.1", "0.5", "1", "5", "10", "50", "100"]:
    send_args = [mb]
    
    for loss in ["0", "0.1", "0.2", "0.3"]:
        receive_args = ["output.txt", loss]
 
        total_time = 0
        for i in range(5):
            
            # Run first script
            receive_result = subprocess.Popen(
                [sys.executable, "receiver_stopwait.py", *receive_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(1)
            # Run second script
            send_result = subprocess.Popen(
                [sys.executable, "sender_stopwait.py", *send_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            send_out, send_err = send_result.communicate()
            receive_result.terminate()
            recv_out, recv_err = receive_result.communicate()

            print(send_out)
        #     total_time += float(send_out.split("time=")[1].split()[0])
        # print("SIZE: " + mb + "MB | " + "LOSS: " + loss + "% | AVG OF 5 RUNS: " + str(total_time / 5))
