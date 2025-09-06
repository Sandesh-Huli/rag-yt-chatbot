from chatbot.services.transcript_service import fetch_youtube_transcript
from chatbot.models.llm import get_llm_response
from chatbot.services.rag_service import RAG
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
import uuid, json, re
from langgraph.graph import StateGraph, END, START
from chatbot.services.db_service import DBService  # integrate DB
from chatbot.parsers.orchestrator_parser import structured_llm, Orchestrator
from chatbot.tools.web_search import web_search
from langchain_core.tools import Tool
from dotenv import load_dotenv

web_search_tool = Tool(
    name="web_search",
    func=web_search,
    description="useful for answering questions that require up-to-date information from the web."
)

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
rag = RAG()
db = DBService()
# ---------------- Orchestrator Output Parser ----------------


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
    You are not a chatbot. You are an orchestrator.
    Your ONLY job is to decide which mode to use for the YouTube assistant.
    You must always respond with EXACTLY one JSON object and nothing else.

    The valid modes are:
    - "qa" → if the user asks a specific question about the video transcript.
    - "summarize" → if the user asks for a summary.
    - "translate" → if the user asks to translate into another language.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state.query}
    ]
    
    try:
        parsed: Orchestrator = structured_llm(messages)
        print(f"\nStructured output from llm = {parsed.mode}\n")
        state.mode = parsed.mode
    except Exception as e:
        print(f"\n[orchestrator fallback due to error: {e}]\n")
        state.mode = "qa"  # safe fallback

    return state


def qa_node(state: AgentState) -> AgentState:
    print("\nqa node was called by the orchestrator\n")
    transcript_text=""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])
        
    tool_prompt = (
        "You are a helpful assistant. If the answer is not in the transcript or chat history, "
        "respond ONLY with the word 'search' (no punctuation). Otherwise, respond with the word 'not needed'.\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"User Question: {state.query}"
    ) 
    tool_decision = get_llm_response(tool_prompt)
    # tool_decision_text = tool_decision.content.strip().lower() if hasattr(tool_decision, "content") else str(tool_decision).strip().lower()
    tool_decision_text = getattr(tool_decision, "content", str(tool_decision)).strip().lower()
    print(tool_decision_text)
    if tool_decision_text == "search":
        web_results = web_search_tool.run(state.query)
        prompt = (
            "You are a helpful assistant. Use the following web search results and previous chat history to answer the user's question.\n\n"
            f"Web Search Results:\n{web_results}\n\n"
            f"Chat History:\n{history_text}\n\n"
            f"User Question: {state.query}"
        )
    else:
    # Build the prompt for the agent
        prompt = (
            "You are a helpful assistant. Use the following transcript and previous chat history to answer the user's question.\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            f"Chat History:\n{history_text}\n\n"
            f"User Question: {state.query}"
        )
    result = get_llm_response(prompt)
    state.result = getattr(result, "content", str(result))
    # Save query + answer into RAG memory
    query_text = state.query.content if hasattr(state.query, "content") else str(state.query)
    rag.add_query(query_text, {"role": "user"})
    
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})
    
    return state

def summarize_node(state: AgentState) -> AgentState:
    print("\nsummarize node was called by the orchestrator\n")
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
    
    result = get_llm_response(prompt)
    state.result = getattr(result, "content", str(result))
    query_text = state.query.content if hasattr(state.query, "content") else str(state.query)
    rag.add_query(query_text, {"role": "user"})
    
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})
    return state

def translate_node(state: AgentState) -> AgentState:
    print("\ntranslate node was called by the orchestrator\n")
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
        f"Translation:\n({state.target_language})"
    )
    
    result = get_llm_response(prompt, target_language=state.target_language)
    state.result = getattr(result, "content", str(result))

    rag.add_query(f"translate video to {state.target_language}", {"role": "user"})
    # If state.result is an LLM message object, extract the content
    result_text = state.result.content if hasattr(state.result, "content") else str(state.result)
    rag.add_query(result_text, {"role": "assistant"})

def fallback_node(state: AgentState) -> AgentState:
    print("\nfallback node was called by the orchestrator\n")
    state.result = "I didn’t understand your query. Could you please rephrase?"
    return state


# ---------------- Graph Setup ----------------
graph = StateGraph(AgentState)

graph.add_node("fetch_transcript", fetch_transcript_node)
graph.add_node("add_transcript", add_transcript_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("qa", qa_node)
graph.add_node("summarize", summarize_node)
graph.add_node("translate", translate_node)
graph.add_node("fallback", fallback_node)

graph.add_edge(START, "fetch_transcript")
graph.add_edge("fetch_transcript", "add_transcript")
graph.add_edge("add_transcript", "orchestrator")

graph.add_conditional_edges(
    "orchestrator",
    lambda state: state.mode,
    {"qa": "qa", "summarize": "summarize", "translate": "translate","fallback":"fallback"}
)

graph.add_edge("qa", END)
graph.add_edge("summarize", END)
graph.add_edge("translate", END)
graph.add_edge("fallback",END)

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
