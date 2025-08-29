from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from langgraph.graph import StateGraph, END, START
from langchain_google_genai import ChatGoogleGenerativeAI

from chatbot.services.agent_service import Chatbot

from dotenv import load_dotenv

# Agent State
@dataclass
class AgentState:
    video_id: str
    query: str
    lang: str = "en"
    top_k: int = 3
    target_language: str = "en"
    transcript_segments: Optional[List[str]] = field(default=None)
    retrieved_chunks: Optional[List[Dict[str, Any]]] = field(default=None)
    mode: Optional[str] = None   # "qa", "summarize", "translate"
    result: Optional[str] = field(default=None)

# Instantiate LLM + Chatbot
load_dotenv()
chatbot = Chatbot()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3
)

# Graph Node Functions
def fetch_transcript_node(state: AgentState) -> AgentState:
    transcript = chatbot.fetch_transcript_node(state.video_id, lang=state.lang)
    state.transcript_segments = transcript
    return state


def add_transcript_node(state: AgentState) -> AgentState:
    chatbot.transcript_segments = state.transcript_segments
    chatbot.add_transcript_node(meta={"video_id": state.video_id})
    return state


def orchestrator_node(state: AgentState) -> AgentState:
    """
    Use LLM to decide which mode to pick (qa, summarize, translate),
    or directly answer from knowledge if context isn't needed.
    """
    system_prompt = """
    You are a YouTube RAG chatbot with multiple abilities:
    - You can answer user questions from the video transcript (qa).
    - You can summarize the video (summarize).
    - You can translate the transcript into a target language (translate).
    - You may also answer from your general knowledge if the transcript is not needed.

    Decide the best action:
    1. "qa" if the user asks a specific question about the video.
    2. "summarize" if the user asks for a summary.
    3. "translate" if the user asks to translate into another language.
    4. "direct" if you can answer from your knowledge without transcript.

    Respond in JSON with a single key "mode".
    Example: {"mode": "qa"}
    """

    msg = llm.invoke([{"role": "system", "content": system_prompt},
                      {"role": "user", "content": state.query}])
    
    try:
        import json
        state.mode = json.loads(msg.content)["mode"]
    except Exception:
        state.mode = "qa"  # fallback
    return state


def qa_node(state: AgentState) -> AgentState:
    chunks = chatbot.retrieve_chunks_node(state.query)
    state.result = chatbot.qa_node(state.query, chunks)
    return state


def summarize_node(state: AgentState) -> AgentState:
    chunks = chatbot.retrieve_chunks_node("summarize")
    state.result = chatbot.summarize_node(chunks)
    return state


def translate_node(state: AgentState) -> AgentState:
    chunks = chatbot.retrieve_chunks_node("translate")
    state.result = chatbot.translate_node(chunks, target_language=state.target_language)
    return state


def direct_node(state: AgentState) -> AgentState:
    """LLM just answers directly, no transcript used."""
    msg = llm.invoke(state.query)
    state.result = msg.content
    return state

# Build LangGraph
graph = StateGraph(AgentState)

graph.add_node("fetch_transcript", fetch_transcript_node)
graph.add_node("add_transcript", add_transcript_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("qa", qa_node)
graph.add_node("summarize", summarize_node)
graph.add_node("translate", translate_node)
graph.add_node("direct", direct_node)

graph.add_edge(START, "fetch_transcript")
graph.add_edge("fetch_transcript", "add_transcript")
graph.add_edge("add_transcript", "orchestrator")

# Dynamic routing after orchestrator
graph.add_conditional_edges(
    "orchestrator",
    lambda state: state.mode,
    {
        "qa": "qa",
        "summarize": "summarize",
        "translate": "translate",
        "direct": "direct",
    },
)

graph.add_edge("qa", END)
graph.add_edge("summarize", END)
graph.add_edge("translate", END)
graph.add_edge("direct", END)

yt_agent_graph = graph.compile()

if __name__ == "__main__":
    state = AgentState(
        video_id=input("Enter YouTube video_id: "),
        query=input("Enter your query: "),
        lang="en",
        top_k=3,
        target_language="hi"
    )
    final_state = yt_agent_graph.invoke(state)
    print("\nAgent Response:\n", final_state["result"])
