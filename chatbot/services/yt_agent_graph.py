from chatbot.services.transcript_service import fetch_youtube_transcript
from chatbot.models.llm import get_llm_response
from chatbot.services.rag_service import RAG
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

from langgraph.graph import StateGraph, END, START

# from chatbot.services.agent_service import Chatbot
from chatbot.services.db_service import DBService  # integrate DB
from dotenv import load_dotenv

# ---------------- Agent State ----------------
@dataclass
class AgentState:
    user_id: str
    session_id: str
    video_id: str
    query: str
    lang: str = "en"
    top_k: int = 3
    target_language: str = "en"
    transcript_segments: Optional[List[str]] = field(default=None)
    retrieved_chunks: Optional[List[Dict[str, Any]]] = field(default=None)
    mode: Optional[str] = None
    result: Optional[str] = None
    history: Optional[List[Dict[str,str]]] = field(default=None)

# ---------------- Setup ----------------
load_dotenv()
# chatbot = Chatbot()
rag = RAG()
db = DBService()


# ---------------- Graph Nodes ----------------
def fetch_transcript_node(state: AgentState) -> AgentState:
    
    state.transcript_segments =  fetch_youtube_transcript(state.video_id,state.lang)
    return state

def add_transcript_node(state: AgentState) -> AgentState:
    if not state.transcript_segments:
        raise RuntimeError("No transcript loaded. Please fetch transcript first.")
    rag.add_transcript(state.transcript_segments, meta={"video_id": state.video_id})
    return state

def orchestrator_node(state: AgentState) -> AgentState:
    system_prompt = """
    Use LLM to decide which mode to pick (qa, summarize, translate),
    or directly answer from knowledge if context isn't needed.
    
    You are a YouTube RAG chatbot with multiple abilities:
    - Answer user questions from transcript (qa).
    - Summarize the video (summarize).
    - Translate transcript into another language (translate).
    - Or answer directly if transcript is not needed.

    Decide the best action:
    1. "qa" if the user asks a specific question about the video.
    2. "summarize" if the user asks for a summary.
    3. "translate" if the user asks to translate into another language.
    
    Respond in JSON with a single key "mode".
    Example: {"mode": "qa"}

    """
    
    messages = (state.history or []) + [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state.query}
    ]
    
    msg = get_llm_response(messages)
    try:
        import json
        state.mode = json.loads(msg.content)["mode"]
    except Exception:
        state.mode = "qa"
    finally:
        print(f"\n{state.mode} was called by the orchestrator\n")
    return state

def qa_node(state: AgentState) -> AgentState:
    transcript_text=""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])
    
    # Build the prompt for the agent
    prompt = (
        "You are a helpful assistant. Use the following transcript and previous chat history to answer the user's question.\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"User Question: {state.query}"
    )
    state.result = get_llm_response(prompt)
    # Save query + answer into RAG memory
    query_text = state.query.content if hasattr(state.query, "content") else str(state.query)
    rag.add_query(query_text, {"role": "user"})
    
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})
    
    return state

def summarize_node(state: AgentState) -> AgentState:
    transcript_text = ""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])
        
    prompt = (
        "You are a helpful assistant. Summarize the following YouTube video transcript, considering the previous chat history for context.\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Chat History:\n{history_text}\n\n"
        "Summary:"
    )
    
    state.result = get_llm_response(prompt)
    query_text = state.query.content if hasattr(state.query, "content") else str(state.query)
    rag.add_query(query_text, {"role": "user"})
    
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})
    return state

def translate_node(state: AgentState) -> AgentState:
    transcript_text = ""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])

    prompt = (
        f"You are a helpful assistant. Translate the following YouTube video transcript into {state.target_language}, considering the previous chat history for context.\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"Translation ({state.target_language}):"
    )
    
    state.result = get_llm_response(prompt, target_language=state.target_language)

    rag.add_query(f"translate video to {state.target_language}", {"role": "user"})
    # If state.result is an LLM message object, extract the content
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})


# ---------------- Graph Setup ----------------
graph = StateGraph(AgentState)

graph.add_node("fetch_transcript", fetch_transcript_node)
graph.add_node("add_transcript", add_transcript_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("qa", qa_node)
graph.add_node("summarize", summarize_node)
graph.add_node("translate", translate_node)

graph.add_edge(START, "fetch_transcript")
graph.add_edge("fetch_transcript", "add_transcript")
graph.add_edge("add_transcript", "orchestrator")

graph.add_conditional_edges(
    "orchestrator",
    lambda state: state.mode,
    {"qa": "qa", "summarize": "summarize", "translate": "translate"}
)

graph.add_edge("qa", END)
graph.add_edge("summarize", END)
graph.add_edge("translate", END)

yt_agent_graph = graph.compile()

def run_query(user_id: str, session_id: str, video_id: str, query: str) -> str:
    # Load previous history for this session
    history = db.get_chat_history(user_id, video_id,session_id) or []
    # Format history into messages for the LLM
    history_msgs = []
    if history:
        for msg in history.messages:
            role = msg.role
            content = msg.message
            history_msgs.append({"role": role, "content": content})
    # Add the new user query
    history_msgs.append({"role": "user", "content": query})
    print(history_msgs)

    rag.add_query(query,{"role":"user"})
    # Run the graph
    state = AgentState(
        user_id=user_id,
        session_id=session_id,
        video_id=video_id,
        query=query,
        history=history_msgs  # <-- new field in AgentState
        
    )
    final_state = yt_agent_graph.invoke(
        state,
        config={"configurable": {"session_id": state.session_id}}
    )
    # print(final_state.result)
    answer = final_state["result"]

    # Save to DB
    db.add_message(user_id, video_id, session_id, "user", query)
    
    assistant_message = answer.content if hasattr(answer, "content") else str(answer)
    db.add_message(user_id, video_id, session_id, "assistant", assistant_message)

    rag.add_query(assistant_message,{"role":"assistant"})
    
    return assistant_message


# ---------------- Main Loop ----------------
if __name__ == "__main__":
    # Ask once for thread_id + video_id, then continue chat loop
    session_id = input("Enter session_id (leave blank for new): ").strip() or str(uuid.uuid4())
    user_id = input("Enter user_id (leave blank for new): ").strip() or str(uuid.uuid4())
    video_id = input("Enter YouTube video_id: ")

    print("\n💬 Chat started. Type 'quit' to exit.\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit"]:
            print("👋 Chat ended.")
            break

        response = run_query(user_id,session_id, video_id, query)
        
        print("Assistant:", response)
