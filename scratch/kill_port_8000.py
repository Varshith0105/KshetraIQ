import subprocess
import re

out = subprocess.check_output("netstat -ano", shell=True).decode()
pids = set()
for line in out.splitlines():
    if ":8000" in line and "LISTENING" in line:
        parts = line.strip().split()
        pid = parts[-1]
        pids.add(pid)

print("Found listening PIDs on 8000:", pids)
for pid in pids:
    print(f"Killing PID {pid}...")
    subprocess.run(f"taskkill /F /PID {pid}", shell=True)

print("Finished killing port 8000 processes.")
