# MCP_Server
MCP server for Job finding and automatic Job application
# MCP Server — Job Finder & Auto Job Application

This project is an **automatic MCP server** built for the Puch AI hackathon.  
It provides tools for job searching, analyzing job descriptions, fetching job postings from URLs, and automatic job application submission by uploading resumes.

---

## Features

- **Job Searching:** Search for jobs using free-text goals or queries.  
- **Job Description Analysis:** Analyze and suggest improvements for job descriptions or user goals.  
- **URL Fetching:** Fetch and simplify job postings from given URLs.  
- **Auto-Apply:** Automatically fill and submit job application forms on websites by uploading your resume.  
- **Image Tool:** Convert base64-encoded images to black and white.

---

## Architecture & Tech Stack

- **FastAPI:** Web framework for the HTTP server and REST API.  
- **FastMCP:** Micro-Component Protocol server framework to build MCP tools.  
- **Playwright:** Browser automation to autofill and submit job applications.  
- **HTTPX:** Async HTTP client for fetching URLs and search results.  
- **Readabilipy & Markdownify:** Extract and simplify web page content to markdown.  
- **Pillow (PIL):** Image processing for black & white conversion.  
- **Python 3.13+**  

---

## Setup & Deployment

### Prerequisites

- Python 3.13 or higher  
- [Playwright browsers](https://playwright.dev/python/docs/intro#install-browsers): Run  
  `bash
  playwright install
Installation
1. clone the repo -
git clone https://github.com/DragonBGW/MCP_Server.git
cd MCP_Server

2. Create and activate a virtual environment (recommended):
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

3. Install dependencies:
pip install -r requirements.txt

4. Install Playwright browsers:
playwright install

Running the Server
python mcp_starter.py

The server will run on http://0.0.0.0:8086 by default.
Visit http://localhost:8086/ to verify the server is running.

After running job_applicant.py in your terminal, it will require your details. 
<img width="482" height="143" alt="image" src="https://github.com/user-attachments/assets/01fc0da4-9e91-4c61-abf6-cac838e108df" />

The html file shows the web Interface of the server
<img width="479" height="264" alt="image" src="https://github.com/user-attachments/assets/d374a967-6c97-4c64-b310-6adf83f00aa8" />

