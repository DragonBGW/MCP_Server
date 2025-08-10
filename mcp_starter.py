# mcp_starter.py - Corrected Version
import asyncio
import os
import base64
import io
import tempfile
from typing import Annotated, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair  # Updated from deprecated BearerAuthProvider
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, AnyUrl
import markdownify
import httpx
import readabilipy
from bs4 import BeautifulSoup
from PIL import Image
from playwright.async_api import async_playwright
from fastapi.middleware.cors import CORSMiddleware

# --- Load environment variables ---
load_dotenv()
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Updated Auth Provider using JWTVerifier ---
class SimpleJWTVerifier(JWTVerifier):
    def __init__(self, token: str):
        key_pair = RSAKeyPair.generate()
        super().__init__(
            public_key=key_pair.public_key,
            issuer=None,
            audience=None
        )
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None
            )
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- Fetch Utility Class ---
class Fetch:
    USER_AGENT = "Puch/1.0 (Autonomous)"

    @classmethod
    async def fetch_url(cls, url: str, user_agent: str, force_raw: bool = False) -> tuple[str, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, follow_redirects=True, headers={"User-Agent": user_agent}, timeout=30)
            except httpx.HTTPError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))
            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url} - status code {response.status_code}"))
            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = "text/html" in content_type
        if is_page_html and not force_raw:
            return cls.extract_content_from_html(page_raw), ""
        return page_raw, f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n"

    @staticmethod
    def extract_content_from_html(html: str) -> str:
        ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
        if not ret or not ret.get("content"):
            return "<error>Page failed to be simplified from HTML</error>"
        return markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)

    @staticmethod
    async def google_search_links(query: str, num_results: int = 5) -> list[str]:
        ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        links = []
        async with httpx.AsyncClient() as client:
            resp = await client.get(ddg_url, headers={"User-Agent": Fetch.USER_AGENT})
            if resp.status_code != 200:
                return ["<error>Failed to perform search.</error>"]
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", class_="result__a", href=True):
            href = a["href"]
            if "http" in href:
                links.append(href)
            if len(links) >= num_results:
                break
        return links or ["<error>No results found.</error>"]

# --- MCP Server Setup ---
mcp = FastMCP(
    "Job Finder MCP Server",
    auth=SimpleJWTVerifier(TOKEN),
    stateless_http=True,
    json_response=True
)

# CORS Configuration
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8086",
    "http://127.0.0.1:8086",
]

# Correct way to add middleware to FastMCP
@mcp.app.on_event("startup")
async def startup_event():
    mcp.app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# [Rest of your tools and functions remain exactly the same...]
# --- Tool: validate ---
@mcp.tool
async def validate() -> str:
    """Return the phone number in {country_code}{number} format with only digits."""
    return "".join(ch for ch in MY_NUMBER if ch.isdigit())

# --- Job Finder description ---
JobFinderDescription = RichToolDescription(
    description="Smart job tool: analyze descriptions, fetch URLs, or search jobs based on free text.",
    use_when="Use this to evaluate job descriptions or search for jobs using freeform goals.",
    side_effects="Returns insights, fetched job descriptions, or relevant job links.",
)

# [Rest of your existing code for job_finder, autofill_job_application, etc...]

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())
