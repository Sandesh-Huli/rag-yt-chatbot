"""
LLM utility for generating responses using Gemini 2.5 Flash (Google Generative AI).
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

class LLM:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self.llm = ChatGoogleGenerativeAI(
            model='gemini-2.5-flash',
            api_key=api_key,
            temperature=0
        )

def get_llm_response(prompt: str, target_language: str = None) -> str:
    """
    Calls Gemini 2.5 Flash model with the given prompt and returns the response text.
    """
    llm = LLM()
    response = llm.llm.invoke(prompt)
    # The response is a LangChain Message object; get the content
    return response.content if hasattr(response, "content") else str(response)