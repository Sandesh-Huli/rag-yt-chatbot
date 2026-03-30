from pydantic import BaseModel, Field
from typing import Literal
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

class Orchestrator(BaseModel):
    mode: Literal["qa", "summarize", "translate", "fallback"] = Field(
        default="qa", description="The mode for processing the user query"
    )

def structured_llm(query: str) -> Orchestrator:
    """
    Uses Gemini's structured output to determine the orchestration mode.
    Returns a properly parsed Orchestrator object.
    """
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=api_key,
        temperature=0
    )
    
    # Use structured output with Pydantic model
    structured_llm_tool = llm.with_structured_output(Orchestrator)
    
    system_prompt = """You are an orchestrator that determines how to handle a user's query about a YouTube video.
    
Analyze the query and return the appropriate mode:
- 'qa': If the user is asking a question about the video content
- 'summarize': If the user is asking for a summary of the video
- 'translate': If the user is asking to translate the content
- 'fallback': If you cannot determine the mode

Respond with ONLY the JSON object, no additional text."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    response = structured_llm_tool.invoke(messages)
    return response