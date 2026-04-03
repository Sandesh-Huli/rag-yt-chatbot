from chatbot.services.transcript_service import fetch_youtube_transcript
from chatbot.models.llm import get_llm_response
from chatbot.services.rag_service import RAG
from chatbot.services.cache_manager import video_cache_manager, session_cache_manager
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
import uuid, json, re
from langgraph.graph import StateGraph, END, START
from chatbot.services.db_service import DBService
from chatbot.parsers.orchestrator_parser import structured_llm, Orchestrator
from chatbot.tools.web_search import web_search
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

web_search_tool = Tool(
    name="web_search",
    func=web_search,
    description="useful for answering questions that require up-to-date information from the web."
)

# ---------------- Agent State ----------------
@dataclass
class AgentState:
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
# Two-tier cache: video_id → FAISS index, session_id → chat memory
# Removed global RAG instance; now using cache managers for thread-safe concurrent access
db = DBService()

def extract_response_content(response):
    """Extract string content from LLM response object or string."""
    if hasattr(response, "content"):
        return response.content
    return str(response)


# ---------------- Graph Nodes ----------------
def fetch_transcript_node(state: AgentState) -> AgentState:
    logger.info(f"🎬 Fetching transcript for video: {state.video_id}")
    try:
        state.transcript_segments =  fetch_youtube_transcript(state.video_id,state.lang)
        logger.info(f"✅ Transcript fetched: {len(state.transcript_segments)} segments")
    except Exception as e:
        logger.error(f"❌ YouTube API Error: {str(e)}")
        state.transcript_segments = []
        state.result = f"Error: Could not fetch transcript - {str(e)}"
    return state

def add_transcript_node(state: AgentState) -> AgentState:
    if not state.transcript_segments:
        raise RuntimeError("No transcript loaded. Please fetch transcript first.")
    
    # Get or create video cache for this video_id
    video_cache = video_cache_manager.get_video_cache(state.video_id)
    
    if video_cache.is_indexed():
        logger.info(f"✅ Transcript already indexed for video: {state.video_id}")
        return state
    
    logger.info(f"🔄 Adding transcript to video cache for video: {state.video_id}")
    try:
        video_cache.add_transcript(state.transcript_segments, metadata={"video_id": state.video_id})
        logger.info(f"💾 Transcript embeddings saved to FAISS")
    except Exception as e:
        logger.error(f"❌ FAISS/Embedding Error: {str(e)}")
        state.result = f"Error: Could not process transcript embeddings - {str(e)}"
    return state


def orchestrator_node(state: AgentState) -> AgentState:
    logger.info(f"🎯 Orchestrator analyzing query: {state.query[:50]}...")
    
    try:
        # Call structured_llm with the query - it handles the structured output
        orchestrator_response: Orchestrator = structured_llm(state.query)
        logger.info(f"✅ Orchestrator selected mode: {orchestrator_response.mode}")
        state.mode = orchestrator_response.mode
    except Exception as e:
        logger.warning(f"⚠️ Orchestrator fallback due to error: {e}")
        state.mode = "qa"  # safe fallback

    return state


def qa_node(state: AgentState) -> AgentState:
    logger.debug("QA node called")
    transcript_text=""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])
        
    # Safe prompt template to prevent injection
    tool_template = PromptTemplate(
        input_variables=["transcript", "history", "query"],
        template="You are a helpful assistant. If the answer is not in the transcript or chat history, "
                 "respond ONLY with the word 'search' (no punctuation). Otherwise, respond with the word 'not needed'.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "User Question: {query}"
    )
    tool_prompt = tool_template.format(transcript=transcript_text, history=history_text, query=state.query)
    tool_decision = get_llm_response(tool_prompt)
    tool_decision_text = extract_response_content(tool_decision).strip().lower()
    logger.debug(f"Tool decision: {tool_decision_text}")
    if tool_decision_text == "search":
        try:
            web_results = web_search_tool.run(state.query)
        except Exception as e:
            logger.error(f"❌ Web Search Error: {str(e)}")
            web_results = "[Web search unavailable]"
        # Safe prompt template for search path
        search_template = PromptTemplate(
            input_variables=["web_results", "history", "query"],
            template="You are a helpful assistant. Use the following web search results and previous chat history to answer the user's question.\n\n"
                     "Web Search Results:\n{web_results}\n\n"
                     "Chat History:\n{history}\n\n"
                     "User Question: {query}"
        )
        prompt = search_template.format(web_results=web_results, history=history_text, query=state.query)
    else:
    # Safe prompt template for transcript path
        transcript_template = PromptTemplate(
            input_variables=["transcript", "history", "query"],
            template="You are a helpful assistant. Use the following transcript and previous chat history to answer the user's question.\n\n"
                     "Transcript:\n{transcript}\n\n"
                     "Chat History:\n{history}\n\n"
                     "User Question: {query}"
        )
        prompt = transcript_template.format(transcript=transcript_text, history=history_text, query=state.query)
    try:
        result = get_llm_response(prompt)
        state.result = extract_response_content(result)
    except Exception as e:
        logger.error(f"❌ LLM API Error: {str(e)}")
        state.result = f"Error: Could not generate response - {str(e)}"
        return state
    # Save query + answer into session cache (per-session memory)
    try:
        session_cache = session_cache_manager.get_session_cache(state.session_id)
        query_text = extract_response_content(state.query)
        session_cache.add_message(query_text, {"role": "user"})
        session_cache.add_message(state.result, {"role": "assistant"})
    except Exception as e:
        logger.error(f"❌ Session Memory Storage Error: {str(e)}")
    
    return state

def summarize_node(state: AgentState) -> AgentState:
    logger.debug("Summarize node called")
    transcript_text = ""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])
        
    # Safe prompt template to prevent injection
    summary_template = PromptTemplate(
        input_variables=["transcript", "history"],
        template="You are a helpful assistant. Summarize the following YouTube video transcript, considering the previous chat history for context.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "Summary:"
    )
    prompt = summary_template.format(transcript=transcript_text, history=history_text)
    
    try:
        result = get_llm_response(prompt)
        state.result = extract_response_content(result)
    except Exception as e:
        logger.error(f"❌ LLM API Error in summarize: {str(e)}")
        state.result = f"Error: Could not generate summary - {str(e)}"
        return state
    
    try:
        query_text = extract_response_content(state.query)
        rag.add_query(query_text, {"role": "user"})
        rag.add_query(state.result, {"role": "assistant"})
    except Exception as e:
        logger.error(f"❌ RAG Query Storage Error in summarize: {str(e)}")
    return state

def translate_node(state: AgentState) -> AgentState:
    logger.debug("Translate node called")
    transcript_text = ""
    if state.transcript_segments:
        transcript_text = "\n".join(state.transcript_segments)

    history_text = ""
    if state.history:
        history_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in state.history if m.get("role") and m.get("content")])

    # Safe prompt template to prevent injection
    translate_template = PromptTemplate(
        input_variables=["target_language", "transcript", "history"],
        template="You are a helpful assistant. Translate the following YouTube video transcript into {target_language}, considering the previous chat history for context.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "Translation:\n({target_language})"
    )
    prompt = translate_template.format(target_language=state.target_language, transcript=transcript_text, history=history_text)
    
    try:
        result = get_llm_response(prompt, target_language=state.target_language)
        state.result = extract_response_content(result)
    except Exception as e:
        logger.error(f"❌ LLM API Error in translate: {str(e)}")
        state.result = f"Error: Could not generate translation - {str(e)}"
        return state

    try:
        rag.add_query(f"translate video to {state.target_language}", {"role": "user"})
        rag.add_query(state.result, {"role": "assistant"})
    except Exception as e:
        logger.error(f"❌ RAG Query Storage Error in translate: {str(e)}")
    return state

def fallback_node(state: AgentState) -> AgentState:
    logger.debug("Fallback node called")
    state.result = "I didn't understand your query. Could you please rephrase?"
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

def run_query(session_id: str, video_id: str, query: str) -> str:
    logger.info(f"Running query for video: {video_id}, session: {session_id}")
    
    # Load memory state (includes conversation summary if any)
    memory_state = db.get_memory_state(session_id, video_id)
    logger.debug(f"Loaded memory state: {memory_state}")
    
    # Load previous history for this session
    history = db.get_chat_history(session_id) or []
    # Format history into messages for the LLM
    history_msgs = []
    if history:
        for msg in history.messages:
            role = msg.role
            content = msg.message
            # Include conversation summary if available (prepend as context)
            if memory_state and memory_state.get("conversation_summary") and role == "user" and not history_msgs:
                history_msgs.append({
                    "role": "system",
                    "content": f"[Previous conversation summary]: {memory_state.get('conversation_summary')}"
                })
            history_msgs.append({"role": role, "content": content})
    # Add the new user query
    history_msgs.append({"role": "user", "content": query})
    logger.debug(f"History messages count: {len(history_msgs)}")

    # Run the graph
    state = AgentState(
        session_id=session_id,
        video_id=video_id,
        query=query,
        history=history_msgs  # <-- new field in AgentState
        
    )
    final_state = yt_agent_graph.invoke(
        state,
        config={"configurable": {"session_id": state.session_id}}
    )
    answer = final_state["result"]

    # Save to DB
    db.add_message(session_id, video_id, "user", query)
    
    assistant_message = extract_response_content(answer)
    logger.debug(f"Generated response length: {len(assistant_message)} chars")
    db.add_message(session_id, video_id, "assistant", assistant_message)

    # Note: Messages are also stored in session cache (via qa_node) for isolation
    # The session cache acts as a per-session memory store separate from DB
    
    # Check memory and prune if needed (only original messages summarized)
    try:
        # Get session cache to access memory metrics
        session_cache = session_cache_manager.get_session_cache(session_id)
        message_count = session_cache.get_message_count()
        logger.debug(f"Session cache has {message_count} messages")
        
        # Prune via database (maintains original messages filtering)
        updated_memory_state = db.check_and_prune_memory(
            db_service=db,
            session_id=session_id,
            video_id=video_id,
            max_messages=15,
            summary_threshold=20
        ) if hasattr(db, 'check_and_prune_memory') else None
        
        if updated_memory_state:
            logger.info(f"Memory state updated: {message_count} total messages in session cache")
    except Exception as e:
        logger.warning(f"⚠️ Memory pruning skipped: {str(e)}")
    
    return assistant_message


# ============= SESSION & VIDEO CLEANUP FUNCTIONS =============

def cleanup_session(session_id: str) -> bool:
    """Clean up session memory from cache when user logs out or session expires."""
    success = session_cache_manager.cleanup_session(session_id)
    logger.info(f"Session cleanup: {session_id} - {'success' if success else 'not found'}")
    return success


def cleanup_video(video_id: str) -> bool:
    """Clean up video index from cache when no longer needed."""
    success = video_cache_manager.cleanup_video(video_id)
    logger.info(f"Video cleanup: {video_id} - {'success' if success else 'not found'}")
    return success


def cleanup_expired_sessions(days: int = 1) -> int:
    """Periodically clean up expired sessions (default: inactive > 1 day)."""
    count = session_cache_manager.cleanup_expired_sessions(days=days)
    logger.info(f"Cleaned up {count} expired sessions")
    return count


def cleanup_expired_videos(days: int = 7) -> int:
    """Periodically clean up expired video caches (default: not accessed > 7 days)."""
    count = video_cache_manager.cleanup_expired_videos(days=days)
    logger.info(f"Cleaned up {count} expired video caches")
    return count


def get_video_cache_stats() -> Dict[str, Any]:
    """Get statistics about video cache usage."""
    return video_cache_manager.get_cache_stats()


def get_session_cache_stats() -> Dict[str, Any]:
    """Get statistics about session cache usage."""
    return session_cache_manager.get_cache_stats()


# ============= MAIN LOOP =============
if __name__ == "__main__":
    # Ask once for thread_id + video_id, then continue chat loop
    session_id = input("Enter session_id (leave blank for new): ").strip() or str(uuid.uuid4())
    video_id = input("Enter YouTube video_id: ")

    print("\n💬 Chat started. Type 'quit' to exit.\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit"]:
            print("👋 Chat ended.")
            break

        response = run_query(session_id, video_id, query)
        
        print("Assistant:", response)
