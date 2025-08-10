# probe_server.py
import requests, os

HOSTS = ["http://127.0.0.1:8086", "http://localhost:8086"]
paths = ["", "/mcp/", "/mcp", "/"]

for host in HOSTS:
    for p in paths:
        url = host.rstrip("/") + p
        try:
            r = requests.get(url, timeout=3)
            print(f"{url:<40}  -> {r.status_code}")
            # print small body preview
            print(r.text[:400].replace("\n"," ") + "\n")
        except Exception as e:
            print(f"{url:<40}  -> ERROR: {e}")
