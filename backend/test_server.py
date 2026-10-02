import subprocess
import time
import requests
import sys
import os
import signal

# Start uvicorn in background
os.chdir("E:/Projects/FloatChat_v6/FloatChat_v6/backend")
proc = subprocess.Popen([
    "python", "-m", "uvicorn", "app.main:app", 
    "--host", "0.0.0.0", "--port", "8000", "--reload", "--app-dir", "."
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

time.sleep(5)

try:
    # Test health
    r = requests.get("http://localhost:8000/api/health", timeout=5)
    print("Health:", r.status_code, r.json())
    
    # Test forecast
    r = requests.post("http://localhost:8000/api/forecast", 
                     json={"wmoId": "3902114", "cycle": 92}, timeout=60)
    print("Forecast:", r.status_code)
    if r.status_code != 200:
        print("Error:", r.text[:500])
    else:
        print("OK:", r.json().get("forecast_id"))
except Exception as e:
    print("Error:", e)
finally:
    os.kill(proc.pid, signal.SIGTERM)
    proc.wait(timeout=5)