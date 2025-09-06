from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens = None,
        timeout = None,
        max_retries = 2,
        max_output_tokens=512
    )
class Orchestrator(BaseModel):
    mode: Literal["qa", "summarize", "translate", "fallback"] = Field(
        ..., description="You are not a chatbot. You are an orchestrator."
    )

def structured_llm(query: str):
    return llm.with_structured_output(Orchestrator).invoke(query)