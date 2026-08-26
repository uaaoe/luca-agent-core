import asyncio

async def web_search_tool(query: str) -> str:
    """Mock search tool placeholder."""
    await asyncio.sleep(0.5)
    return f"Retrieved context for: '{query}'"
