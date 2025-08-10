import os
import requests
import json
import uuid
import base64

TOKEN = os.getenv("AUTH_TOKEN")
if not TOKEN:
    raise SystemExit("AUTH_TOKEN not set. Set it in your environment before running.")

BASE_URL = "http://127.0.0.1:8086/mcp"  # your MCP server endpoint

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

# Load your resume file and convert to base64
resume_path = "Basu_Chandril_AI.pdf"  # <-- put your actual resume PDF path here
with open(resume_path, "rb") as f:
    resume_base64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "jsonrpc": "2.0",
    "id": str(uuid.uuid4()),
    "method": "tools/call",
    "params": {
        "name": "job_finder",
        "arguments": {
            "user_goal": "Apply for remote Python backend jobs",
            "job_description": None,
            "job_url": "https://example-job-application-url.com",  # <-- replace with actual job application URL
            "raw": False,
            "resume_base64": resume_base64,
            "name": "Your Full Name",  # <-- your full name here
            "email": "your.email@example.com"  # <-- your email here
        }
    }
}

try:
    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)
except requests.RequestException as e:
    print("Request failed:", e)
