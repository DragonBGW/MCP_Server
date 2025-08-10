# mcp_starter.py
import asyncio
import os
import base64
import io
import tempfile
from typing import Annotated, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair  # Deprecated, consider updating later
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

# --- Load environment variables ---
load_dotenv()
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider (keeps Bearer auth, deprecated in fastmcp) ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
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
mcp = FastMCP("Job Finder MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:8000",  # replace/add your frontend origin URLs here
    "http://127.0.0.1:8000",
    "http://localhost:8086",
    "http://127.0.0.1:8086",
]
# Add CORS middleware to underlying FastAPI app
mcp.app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# --- Browser automation helper ---
async def autofill_job_application(job_url: str, resume_path: str, name: str, email: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(job_url, wait_until="domcontentloaded")
        selectors = {
            "name": ['input[name="name"]', 'input[id*="name"]', 'input[placeholder*="name"]'],
            "email": ['input[name="email"]', 'input[id*="email"]', 'input[placeholder*="email"]'],
            "resume": ['input[type="file"]', 'input[name*="resume"]', 'input[name*="cv"]']
        }
        for sel in selectors["name"]:
            if await page.locator(sel).count():
                await page.fill(sel, name)
                break
        for sel in selectors["email"]:
            if await page.locator(sel).count():
                await page.fill(sel, email)
                break
        for sel in selectors["resume"]:
            if await page.locator(sel).count():
                await page.set_input_files(sel, resume_path)
                break
        for btn in ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Apply")', 'a:has-text("Apply")']:
            if await page.locator(btn).count():
                await page.click(btn)
                break
        await browser.close()

# --- Tool: job_finder ---
@mcp.tool(description=JobFinderDescription.model_dump_json())
async def job_finder(
    user_goal: Annotated[str, Field(description="The user's goal (description, intent, or freeform query)")],
    job_description: Annotated[Optional[str], Field(description="Full job description text, if available.")] = None,
    job_url: Annotated[Optional[AnyUrl], Field(description="A URL to fetch a job description from.")] = None,
    raw: Annotated[bool, Field(description="Return raw HTML content if True")] = False,
    resume_base64: Annotated[Optional[str], Field(description="Base64-encoded resume to auto-apply")] = None,
    name: Annotated[Optional[str], Field(description="Applicant full name")] = None,
    email: Annotated[Optional[str], Field(description="Applicant email")] = None,
) -> str:
    if job_url and resume_base64 and name and email:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(base64.b64decode(resume_base64))
            resume_path = tmp_file.name
        try:
            await autofill_job_application(str(job_url), resume_path, name, email)
            return f"✅ Application submitted successfully at {job_url}"
        except Exception as e:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Auto-apply failed: {e}"))
        finally:
            try:
                os.remove(resume_path)
            except Exception:
                pass

    if job_description:
        return f"📝 **Job Description Analysis**\n\n---\n{job_description.strip()}\n---\n\nUser Goal: **{user_goal}**\n\n💡 Suggestions:\n- Tailor your resume.\n- Highlight relevant skills.\n- Consider applying if relevant."

    if job_url:
        content, _ = await Fetch.fetch_url(str(job_url), Fetch.USER_AGENT, force_raw=raw)
        return f"🔗 **Fetched Job Posting from URL**: {job_url}\n\n---\n{content.strip()}\n---\n\nUser Goal: **{user_goal}**"

    if "look for" in user_goal.lower() or "find" in user_goal.lower() or "job" in user_goal.lower():
        links = await Fetch.google_search_links(user_goal)
        return f"🔍 **Search Results for**: _{user_goal}_\n\n" + "\n".join(f"- {link}" for link in links)

    raise McpError(ErrorData(code=INVALID_PARAMS, message="Please provide either a job description, a job URL, a resume+URL+name+email for auto-apply, or a search query in user_goal."))

# --- Image tool ---
MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
    description="Convert an image to black and white and save it.",
    use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
    side_effects="The image will be processed and saved in a black and white format.",
)

@mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
async def make_img_black_and_white(
    puch_image_data: Annotated[Optional[str], Field(description="Base64-encoded image data to convert to black and white")] = None,
) -> list[TextContent | ImageContent]:
    try:
        image_bytes = base64.b64decode(puch_image_data)
        image = Image.open(io.BytesIO(image_bytes))
        bw_image = image.convert("L")
        buf = io.BytesIO()
        bw_image.save(buf, format="PNG")
        bw_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server (stateless HTTP) on http://0.0.0.0:8086 (streamable-http, stateless, json responses). Use HTTPS in production.")
    await mcp.run_async(
        "streamable-http",
        host="0.0.0.0",
        port=8086,
        stateless_http=True,
        json_response=True,
    )

if __name__ == "__main__":
    asyncio.run(main())
