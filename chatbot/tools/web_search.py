from langchain_google_community import GoogleSearchAPIWrapper
import logging
import os
from chatbot.logging_config import get_logger

logger = get_logger(__name__)

def web_search(query : str, count : int = 3):
    """
    Uses LangChain's GoogleSearchAPIWrapper to perform a web search and return the top results as a string.
    Returns error message if search fails.
    """
    try:
        # Pass credentials explicitly (uses GOOGLE_SEARCH_API_KEY env var)
        google_api_key = os.getenv('GOOGLE_SEARCH_KEY') or os.getenv('GOOGLE_API_KEY')
        google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
        search = GoogleSearchAPIWrapper(
            google_api_key=google_api_key,
            google_cse_id=google_cse_id,
            k=count
        )
        response = search.run(query=query)
        if not response:
            logger.warning("No search results found", {
                "event_type": "web_search_no_results",
                "query_length": len(query),
            })
            return "[No search results found]"
        return response
    except Exception as e:
        # Log error without exposing sensitive data (API key is in the exception)
        error_type = type(e).__name__
        logger.error("Web search failed", {
            "event_type": "web_search_error",
            "error_type": error_type,
            "query_length": len(query),
        })
        # Return generic error message (no sensitive details)
        return f"[Web search failed: {error_type}]"