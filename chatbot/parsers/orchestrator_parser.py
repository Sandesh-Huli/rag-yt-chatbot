from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from chatbot.models.llm import LLM

class Orchestrator(BaseModel):
    mode: Literal["qa", "summarize", "translate", "fallback"] = Field(
        ..., description="You are not a chatbot. You are an orchestrator."
    )

def structured_llm(query: str):
    """
    You are an orchestrator. Respond ONLY with a JSON object in this format:
    {"mode": "qa"} or {"mode": "summarize"} or {"mode": "translate"}
    Do not include any explanation or extra text.
    """
    llm = LLM()
    response = llm.llm.invoke(query)
    return response.content