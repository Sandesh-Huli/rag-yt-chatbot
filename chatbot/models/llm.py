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
    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.5-flash",
    #     temperature=0,
    #     max_tokens = None,
    #     timeout = None,
    #     max_retries = 2,
    #     max_output_tokens=512
    # )
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('PPLX_API_KEY')
        self.llm = ChatPerplexity(temperature=0, pplx_api_key=api_key, model="sonar")

def get_llm_response(prompt: str, target_language: str = None) -> str:
    # """
    # Calls Gemini (Google Generative AI) with the given prompt and returns the response text.
    # """
    """
    Calls llama sonar AI model (Perplexity) with the given prompt and return the response text.
    """

    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.5-flash",
    #     temperature=0,
    #     max_tokens =     None,
    #     timeout = None,
    #     max_retries = 2,
    #     max_output_tokens=512
    # )
    llm = LLM()
    # llm = init_chat_model("llama-3-sonar-small-32k-online", model_provider="perplexity")
    response = llm.llm.invoke(prompt)
    # The response is a LangChain Message object; get the content
    return response.content if hasattr(response, "content") else str(response)