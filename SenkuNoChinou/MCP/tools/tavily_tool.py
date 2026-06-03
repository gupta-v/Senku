import os
import logging
from typing import Literal

from dotenv import load_dotenv
from tavily import TavilyClient
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import TavilySearchInput

load_dotenv()
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> str:
    """
    Run a web search using Tavily.

    Description: Searches the web and returns relevant results for the given query.
    Supports general, news, and finance topic filters.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return. Default 5.
        topic: Search category — "general", "news", or "finance". Default "general".
        include_raw_content: Include full raw page content. Default False.

    Returns:
        Search results as a formatted string.
    """
    response = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
        include_raw_content=include_raw_content,
    )
    results = response.get("results", [])
    if not results:
        return "No results found."
    parts = []
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        content = r.get("raw_content") or r.get("content", "")
        content_type = "full" if r.get("raw_content") else "snippet"
        part = (
            f"[{i}] {r.get('title', 'No title')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Score: {score:.4f} | Content: {content_type}\n\n"
            f"{content}"
        )
        parts.append(part)
    return "\n\n---\n\n".join(parts)


# LangChain tool — used directly by the LangGraph agent
tavily_lc_tool = tool(internet_search, args_schema=TavilySearchInput)
