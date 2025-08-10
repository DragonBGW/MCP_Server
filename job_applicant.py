import os
import requests
import json
import uuid
import base64

TOKEN = os.getenv("AUTH_TOKEN")
if not TOKEN:
    raise SystemExit("AUTH_TOKEN not set. Set it in your environment before running.")

BASE_URL = "http://127.0.0.1:8086/mcp"  # MCP Server URL

def apply_to_job(job_url: str, resume_path: str, name: str, email: str):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    with open(resume_path, "rb") as f:
        resume_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": "job_finder",
            "arguments": {
                "user_goal": "",
                "job_description": None,
                "job_url": job_url,
                "raw": False,
                "resume_base64": resume_b64,
                "name": name,
                "email": email
            }
        }
    }

    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code == 200:
        result = resp.json()
        return result.get("result", {}).get("content", [{"text": "No response"}])[0].get("text", "")
    else:
        return f"Error: {resp.status_code} - {resp.text}"

if __name__ == "__main__":
    url = input("Enter job application URL: ")
    resume = input("Enter path to your resume PDF: ")
    name = input("Enter your full name: ")
    email = input("Enter your email: ")

    result = apply_to_job(url, resume, name, email)
    print("\nApplication result:\n", result)
