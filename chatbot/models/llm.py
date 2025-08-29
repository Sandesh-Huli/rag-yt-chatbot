"""
LLM utility for generating responses using Gemini (Google Generative AI).
"""

# import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm_response(prompt: str, target_language: str = None) -> str:
    """
    Calls Gemini (Google Generative AI) with the given prompt and returns the response text.
    """
    load_dotenv()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens = None,
        timeout = None,
        max_retries = 2,
        max_output_tokens=512
    )
    response = llm.invoke(prompt)
    # The response is a LangChain Message object; get the content
    return response.content if hasattr(response, "content") else str(response)