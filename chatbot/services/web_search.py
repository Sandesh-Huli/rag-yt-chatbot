from dotenv import load_dotenv
from langchain_google_community import GoogleSearchAPIWrapper
def web_search(query : str, count : int = 3):
    """
    Uses LangChain's GoogleSearchAPIWrapper to perform a web search and return the top results as a string.
    """
    load_dotenv()
    search = GoogleSearchAPIWrapper(k=count)
    response = search.run(query=query)
    return response
# print(response)