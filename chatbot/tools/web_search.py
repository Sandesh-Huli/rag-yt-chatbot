from langchain_google_community import GoogleSearchAPIWrapper
import logging

logger = logging.getLogger(__name__)

def web_search(query : str, count : int = 3):
    """
    Uses LangChain's GoogleSearchAPIWrapper to perform a web search and return the top results as a string.
    Returns error message if search fails.
    """
    try:
        search = GoogleSearchAPIWrapper(k=count)
        response = search.run(query=query)
        if not response:
            logger.warning(f"No search results found for query: {query}")
            return "[No search results found]"
        return response
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return f"[Web search failed: {str(e)}]"