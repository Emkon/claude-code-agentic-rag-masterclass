import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)
MAX_RESULTS = 5


def _format_tavily_results(results: list[dict]) -> str:
    lines = []
    for r in results[:MAX_RESULTS]:
        lines.append(f"**{r.get('title', '')}**\n{r.get('content', '')}\n{r.get('url', '')}")
    return "\n\n".join(lines)


def _format_ddg_results(results: list[dict]) -> str:
    lines = []
    for r in results[:MAX_RESULTS]:
        lines.append(f"**{r.get('title', '')}**\n{r.get('body', '')}\n{r.get('href', '')}")
    return "\n\n".join(lines)


async def _search_tavily(query: str) -> str:
    from tavily import TavilyClient  # local import — optional dependency
    loop = asyncio.get_event_loop()
    client = TavilyClient(api_key=settings.tavily_api_key)
    response = await loop.run_in_executor(None, lambda: client.search(query, max_results=MAX_RESULTS))
    return _format_tavily_results(response.get("results", []))


async def _search_duckduckgo(query: str) -> str:
    from duckduckgo_search import DDGS  # local import — optional dependency
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, lambda: list(DDGS().text(query, max_results=MAX_RESULTS)))
    return _format_ddg_results(results)


async def search_web(query: str) -> str:
    """
    Search the web. Tries Tavily first (if TAVILY_API_KEY set), falls back to DuckDuckGo.
    Returns "" on any failure — never raises.
    """
    try:
        if settings.tavily_api_key:
            logger.info(f"[web_search] Tavily: {query!r}")
            return await _search_tavily(query)
    except Exception as exc:
        logger.warning(f"[web_search] Tavily failed, trying DuckDuckGo: {exc}")

    try:
        logger.info(f"[web_search] DuckDuckGo: {query!r}")
        return await _search_duckduckgo(query)
    except Exception as exc:
        logger.warning(f"[web_search] DuckDuckGo also failed: {exc}")
        return ""
