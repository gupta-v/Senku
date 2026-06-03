import os
import logging

import requests
from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import JinaReaderInput

load_dotenv()
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

_JINA_API_KEY = os.getenv("JINA_API_KEY")
_JINA_BASE = "https://r.jina.ai"


def browse_url(
    url: str,
    with_links: bool = False,
    with_images: bool = False,
) -> str:
    """
    Fetch a web page and return its content as clean markdown.

    Description: Uses Jina Reader to fetch and convert any public URL into
    LLM-readable markdown. Handles JS-rendered pages. Optionally appends
    a links or images summary.

    Args:
        url: The URL to browse.
        with_links: Append a links summary at the end. Default False.
        with_images: Append an images summary at the end. Default False.

    Returns:
        Page content as clean markdown.
    """
    headers = {"Accept": "text/markdown", "X-Timeout": "30"}
    if _JINA_API_KEY:
        headers["Authorization"] = f"Bearer {_JINA_API_KEY}"
    if with_links:
        headers["X-With-Links-Summary"] = "true"
    if with_images:
        headers["X-With-Images-Summary"] = "true"

    response = requests.get(f"{_JINA_BASE}/{url}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


# LangChain tool — used directly by the LangGraph agent
jina_lc_tool = tool(browse_url, args_schema=JinaReaderInput)
