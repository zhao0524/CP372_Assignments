# Go Back N (GBN)
You can run the automated test using:
```
py runtests_gbn.py
```

Or do a manual run in two terminals using the following commands:
```
py gbn_receiver.py <output_dir> <loss_rate>
py gbn_receiver.py <file_size_mb>
```

---
# Stop and Wait (SAW)

To run, use:

```
py receiver_stopwait.py <loss_rate>
```

Then run:
```
py sender_stopwait.py <file_size_mb>
```

Alternatively, run our custom test to simulate varying loss rates and file sizes:
```
py runtests_saw.py
```