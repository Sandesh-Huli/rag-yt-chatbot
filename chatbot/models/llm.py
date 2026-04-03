"""
LLM utility for generating responses using Gemini 2.5 Flash (Google Generative AI).
"""

import os
from chatbot.config import LLM_MODEL, LLM_TEMPERATURE
from langchain_google_genai import ChatGoogleGenerativeAI

class LLM:
    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            api_key=api_key,
            temperature=LLM_TEMPERATURE
        )

def get_llm_response(prompt: str, target_language: str = None) -> str:
    """
    Calls Gemini 2.5 Flash model with the given prompt and returns the response text.
    """
    llm = LLM()
    response = llm.llm.invoke(prompt)
    # The response is a LangChain Message object; get the content
    return response.content if hasattr(response, "content") else str(response)