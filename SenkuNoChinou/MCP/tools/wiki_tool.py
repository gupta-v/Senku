import os
import logging

import wikipedia as wp
from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import WikiDocument, WikipediaInput, WikipediaOutput

load_dotenv()
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

wp.set_user_agent("SenkuNoChinou/1.0 (personal assistant; vaibhav)")


def _retrieve(query: str) -> list[WikiDocument]:
    docs = []
    for term in wp.search(query, results=10):
        try:
            page = wp.page(term, auto_suggest=False)
            docs.append({"page_content": page.summary, "url": page.url})
        except wp.exceptions.DisambiguationError:
            pass
        if len(docs) >= 2:
            break
    return docs


def ask_wikipedia(question: str) -> str:
    """
    Search Wikipedia and return summaries for the given question.

    Description: Searches Wikipedia and returns up to 2 article summaries
    relevant to the question.

    Args:
        question: The topic or question to search Wikipedia for.

    Returns:
        Concatenated Wikipedia summaries, or a not-found message.
    """
    docs = _retrieve(question)
    if not docs:
        return "No relevant Wikipedia articles found."
    return "\n\n".join(doc["page_content"] for doc in docs)


# LangChain tool — used directly by the LangGraph agent
wiki_lc_tool = tool(ask_wikipedia)
