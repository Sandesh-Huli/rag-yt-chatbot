"""
LLM utility for generating responses using Gemini (Google Generative AI).
"""

import os
import getpass
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.chat_models import init_chat_model
from langchain_perplexity import ChatPerplexity

class LLM:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('PPLX_API_KEY')
        self.llm = ChatPerplexity(temperature=0, pplx_api_key=api_key, model="sonar")

def get_llm_response(prompt: str, target_language: str = None) -> str:
    """
    Calls Perplexity Sonar AI model with the given prompt and returns the response text.
    """
    llm = LLM()
    response = llm.llm.invoke(prompt)
    # The response is a LangChain Message object; get the content
    return response.content if hasattr(response, "content") else str(response)