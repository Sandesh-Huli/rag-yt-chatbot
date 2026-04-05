from chatbot.services.transcript_service import fetch_youtube_transcript
from chatbot.models.llm import get_llm_response
from chatbot.services.rag_service import RAG
from chatbot.services.cache_manager import video_cache_manager, session_cache_manager
from chatbot.config import RETRIEVAL_TOP_K
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
import uuid, json, re
from langgraph.graph import StateGraph, END, START
from chatbot.services.db_service import DBService
from chatbot.parsers.orchestrator_parser import structured_llm, Orchestrator
from chatbot.tools.web_search import web_search
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
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
    top_k: int = RETRIEVAL_TOP_K
    target_language: str = "en"
    transcript_segments: Optional[List[str]] = field(default=None)
    retrieved_chunks: Optional[List[Dict[str, Any]]] = field(default=None)
    mode: Optional[str] = None
    result: Optional[str] = None
    history: Optional[List[Dict[str,str]]] = field(default=None)

# --------------- Setup ---------------
db = DBService()

def extract_response_content(response: Any) -> str:
    """Extract string content from LLM response object or string."""
    if hasattr(response, "content"):
        return response.content
    return str(response)


# ============= HELPER FUNCTIONS (Issue 16: Deduplication) =============

def _build_history_text(history: Optional[List[Dict[str, str]]]) -> str:
    """Build formatted history text from messages (used in qa, summarize, translate nodes).
    
    Args:
        history: List of message dicts with 'role' and 'content' keys
        
    Returns:
        Formatted history string for LLM prompt
    """
    if not history:
        return ""
    
    return "\n".join([
        f'{m["role"]}: {m["content"]}'
        for m in history
        if m.get("role") and m.get("content")
    ])


def _store_to_session_cache(session_id: str, query: str, result: str) -> None:
    """Store query and response to session cache for per-session memory.
    
    Args:
        session_id: Unique session identifier
        query: User's query
        result: Assistant's response
        
    Raises:
        Logs error but doesn't raise (graceful degradation)
    """
    try:
        session_cache = session_cache_manager.get_session_cache(session_id)
        session_cache.add_message(query, {"role": "user"})
        session_cache.add_message(result, {"role": "assistant"})
        logger.debug(f"Stored message pair to session cache for {session_id}")
    except Exception as e:
        logger.error(f"Failed to store message to session cache ({session_id}): {type(e).__name__}: {str(e)}")


def _retrieve_relevant_chunks(video_id: str, query: str, top_k: int = 5) -> str:
    """Retrieve most relevant transcript chunks using semantic search (Issue 23).
    
    Replaces full transcript with top-k retrieved chunks to reduce token usage.
    Falls back to full transcript if FAISS index not available.
    
    Args:
        video_id: YouTube video identifier
        query: Query text for semantic similarity search
        top_k: Number of chunks to retrieve (default 5 for ~1-2KB)
        
    Returns:
        Formatted string of relevant chunks with fallback to full transcript
    """
    try:
        video_cache = video_cache_manager.get_video_cache(video_id)
        
        # If transcript is indexed in FAISS, retrieve semantically relevant chunks
        if video_cache.is_indexed():
            results = video_cache.retrieve_transcript(query, top_k=top_k)
            if results:
                # Format retrieved chunks, separating by dividers
                chunks_text = "\n---\n".join([r['text'] for r in results])
                logger.debug(f"Retrieved {len(results)} highly relevant chunks for semantic search (token-efficient)")
                return chunks_text
            logger.debug("Retrieval returned no results, falling back to full transcript")
    except Exception as e:
        logger.warning(f"FAISS retrieval failed ({type(e).__name__}), using full transcript: {str(e)}")
    
    # Fallback: return full transcript if retrieval fails or not indexed
    logger.debug("Using full transcript as fallback (FAISS not available yet)")
    return ""  # Will use full transcript in calling node


# ----------- Batch Retrieval Helper (Issue 26) ---------

def _retrieve_batch_chunks(video_id: str, queries: List[str], top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve relevant chunks for multiple queries in a single operation (Issue 26).
    
    Batch retrieval improves efficiency when processing multiple queries.
    
    Args:
        video_id: YouTube video identifier
        queries: List of query texts to retrieve chunks for
        top_k: Number of chunks per query (default 3)
        
    Returns:
        Dictionary mapping query to list of retrieved chunk results
    """
    try:
        video_cache = video_cache_manager.get_video_cache(video_id)
        
        if not video_cache.is_indexed():
            logger.debug("Video not indexed in FAISS, batch retrieval unavailable")
            return {q: [] for q in queries}
        
        results = {}
        for query in queries:
            try:
                chunks = video_cache.retrieve_transcript(query, top_k=top_k)
                results[query] = chunks
                logger.debug(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
            except Exception as e:
                logger.error(f"Failed to retrieve chunks for query: {type(e).__name__}: {str(e)}")
                results[query] = []
        
        return results
    except Exception as e:
        logger.error(f"Batch retrieval failed: {type(e).__name__}: {str(e)}")
        return {q: [] for q in queries}


# ---- Batch Search Method for FAISS (Issue 26) ------------ Graph Nodes ----------------
def fetch_transcript_node(state: AgentState) -> AgentState:
    """Fetch YouTube transcript for the given video ID.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with transcript_segments or error message
    """
    logger.info(f"🎬 Fetching transcript for video: {state.video_id}")
    try:
        state.transcript_segments = fetch_youtube_transcript(state.video_id, state.lang)
        logger.info(f"✅ Transcript fetched: {len(state.transcript_segments)} segments")
    except ValueError as e:
        logger.error(f"Invalid video ID format '{state.video_id}': {str(e)}")
        state.result = "Error: Invalid YouTube video ID format. Expected 11-character alphanumeric string."
        state.transcript_segments = []
    except Exception as e:
        logger.error(f"Failed to fetch transcript from YouTube API: {type(e).__name__}: {str(e)}")
        state.result = "Error: Could not fetch video transcript. Please check the video ID and try again."
        state.transcript_segments = []
    
    return state

def add_transcript_node(state: AgentState) -> AgentState:
    """Add transcript to video cache for semantic search.
    
    Args:
        state: Current agent state with transcript_segments
        
    Returns:
        Updated state (or with error message if embedding fails)
        
    Raises:
        RuntimeError: If no transcript loaded
    """
    if not state.transcript_segments:
        logger.error("Cannot index transcript: no segments loaded")
        state.result = "Error: No transcript available to process."
        return state
    
    # Get or create video cache for this video_id
    video_cache = video_cache_manager.get_video_cache(state.video_id)
    
    if video_cache.is_indexed():
        logger.info(f"Transcript already indexed for video: {state.video_id}")
        return state
    
    logger.info(f"Adding transcript to video cache for: {state.video_id}")
    try:
        video_cache.add_transcript(
            state.transcript_segments,
            metadata={"video_id": state.video_id}
        )
        logger.info(f"Successfully embedded and cached transcript ({len(state.transcript_segments)} segments)")
    except Exception as e:
        logger.error(f"Failed to embed transcript: {type(e).__name__}: {str(e)}")
        state.result = "Error: Could not process video transcript for search. Please try again."
    
    return state


def orchestrator_node(state: AgentState) -> AgentState:
    """Determine which operation mode to use (QA, Summarize, Translate, Fallback).
    
    Args:
        state: Current agent state with query
        
    Returns:
        Updated state with selected mode
    """
    logger.info(f"Analyzing query with orchestrator: {state.query[:50]}...")
    
    try:
        # Call structured_llm with the query - it handles the structured output
        orchestrator_response: Orchestrator = structured_llm(state.query)
        logger.info(f"Orchestrator selected mode: {orchestrator_response.mode}")
        state.mode = orchestrator_response.mode
    except ValueError as e:
        logger.warning(f"Orchestrator validation failed (query too long?): {str(e)}")
        state.mode = "qa"  # safe fallback
    except Exception as e:
        logger.warning(f"Orchestrator failed ({type(e).__name__}), using fallback QA mode: {str(e)}")
        state.mode = "qa"  # safe fallback

    return state


def qa_node(state: AgentState) -> AgentState:
    """Answer user question using transcript and/or web search.
    
    Uses orchestrator logic: determine if web search needed, then generate answer.
    Stores interaction in session cache.
    
    Issues Fixed:
    - Issue 23: Uses top-k retrieved chunks instead of full transcript (reduces tokens)
    - Issues 16, 20: Deduplication, type hints, specific error messages
    
    Args:
        state: Current agent state with query, transcript, history
        
    Returns:
        Updated state with result
    """
    logger.debug("Executing QA node")
    
    # Build text content
    # Issue 23: Use retrieved chunks instead of full transcript for token efficiency
    transcript_text = _retrieve_relevant_chunks(state.video_id, state.query, top_k=5)
    if not transcript_text:
        # Fallback to full transcript if retrieval fails
        transcript_text = "\n".join(state.transcript_segments) if state.transcript_segments else ""
    
    history_text = _build_history_text(state.history)
    
    # Determine if web search is needed
    tool_template = PromptTemplate(
        input_variables=["transcript", "history", "query"],
        template="You are a helpful assistant. If the answer is not in the transcript or chat history, "
                 "respond ONLY with the word 'search' (no punctuation). Otherwise, respond with the word 'not needed'.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "User Question: {query}"
    )
    tool_prompt = tool_template.format(transcript=transcript_text, history=history_text, query=state.query)
    
    try:
        tool_decision = get_llm_response(tool_prompt)
        tool_decision_text = extract_response_content(tool_decision).strip().lower()
        logger.debug(f"Tool decision: {tool_decision_text}")
    except Exception as e:
        logger.error(f"Failed to determine search necessity: {type(e).__name__}: {str(e)}")
        state.result = "Error: Could not process your query. Please try again."
        return state
    
    # Route to search or transcript path
    if tool_decision_text == "search":
        try:
            web_results = web_search_tool.run(state.query)
        except Exception as e:
            logger.warning(f"Web search failed, falling back to transcript: {type(e).__name__}: {str(e)}")
            web_results = "[Web search unavailable]"
        
        search_template = PromptTemplate(
            input_variables=["web_results", "history", "query"],
            template="You are a helpful assistant. Use the following web search results and previous chat history to answer the user's question.\n\n"
                     "Web Search Results:\n{web_results}\n\n"
                     "Chat History:\n{history}\n\n"
                     "User Question: {query}"
        )
        prompt = search_template.format(web_results=web_results, history=history_text, query=state.query)
    else:
        transcript_template = PromptTemplate(
            input_variables=["transcript", "history", "query"],
            template="You are a helpful assistant. Use the following transcript and previous chat history to answer the user's question.\n\n"
                     "Transcript:\n{transcript}\n\n"
                     "Chat History:\n{history}\n\n"
                     "User Question: {query}"
        )
        prompt = transcript_template.format(transcript=transcript_text, history=history_text, query=state.query)
    
    # Generate response
    try:
        result = get_llm_response(prompt)
        state.result = extract_response_content(result)
        logger.info(f"QA response generated ({len(state.result)} chars)")
    except Exception as e:
        logger.error(f"LLM API call failed in QA node: {type(e).__name__}: {str(e)}")
        state.result = "Error: Failed to generate response. The AI service is temporarily unavailable."
        return state
    
    # Store to session cache
    _store_to_session_cache(state.session_id, state.query, state.result)
    
    return state

def summarize_node(state: AgentState) -> AgentState:
    """Summarize the video transcript considering chat history for context.
    
    Issue 23: Uses semantically relevant chunks to reduce token usage while
    preserving summary quality. Falls back to full transcript if retrieval unavailable.
    
    Args:
        state: Current agent state with transcript and history
        
    Returns:
        Updated state with summary result
    """
    logger.debug("Executing summarize node")
    
    # Issue 23: Use retrieved chunks instead of full transcript for efficiency
    # For summarization, retrieve broader context (larger top_k)
    transcript_text = _retrieve_relevant_chunks(state.video_id, state.query or "summary", top_k=10)
    if not transcript_text:
        # Fallback to full transcript if retrieval fails
        transcript_text = "\n".join(state.transcript_segments) if state.transcript_segments else ""
    
    history_text = _build_history_text(state.history)
    
    summary_template = PromptTemplate(
        input_variables=["transcript", "history"],
        template="You are a helpful assistant. Summarize the following YouTube video transcript, considering the previous chat history for context.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "Summary:"
    )
    prompt = summary_template.format(transcript=transcript_text, history=history_text)
    
    # Generate summary
    try:
        result = get_llm_response(prompt)
        state.result = extract_response_content(result)
        logger.info(f"Summary generated ({len(state.result)} chars)")
    except Exception as e:
        logger.error(f"LLM API call failed in summarize node: {type(e).__name__}: {str(e)}")
        state.result = "Error: Failed to generate summary. The AI service is temporarily unavailable."
        return state
    
    # Store to session cache
    _store_to_session_cache(state.session_id, state.query, state.result)
    
    return state

def translate_node(state: AgentState) -> AgentState:
    """Translate the video transcript to the target language.
    
    Issue 23: Uses semantically relevant chunks to reduce token usage while
    preserving translation quality. Falls back to full transcript if unavailable.
    
    Args:
        state: Current agent state with transcript and target_language
        
    Returns:
        Updated state with translation result
    """
    logger.debug("Executing translate node")
    
    # Issue 23: Use retrieved chunks instead of full transcript for efficiency
    # For translation, retrieve broader context (larger top_k for completeness)
    transcript_text = _retrieve_relevant_chunks(state.video_id, state.query or "translation", top_k=10)
    if not transcript_text:
        # Fallback to full transcript if retrieval fails
        transcript_text = "\n".join(state.transcript_segments) if state.transcript_segments else ""
    
    history_text = _build_history_text(state.history)

    translate_template = PromptTemplate(
        input_variables=["target_language", "transcript", "history"],
        template="You are a helpful assistant. Translate the following YouTube video transcript into {target_language}, "
                 "considering the previous chat history for context.\n\n"
                 "Transcript:\n{transcript}\n\n"
                 "Chat History:\n{history}\n\n"
                 "Translation:\n({target_language})"
    )
    prompt = translate_template.format(
        target_language=state.target_language,
        transcript=transcript_text,
        history=history_text
    )
    
    # Generate translation
    try:
        result = get_llm_response(prompt, target_language=state.target_language)
        state.result = extract_response_content(result)
        logger.info(f"Translation generated to {state.target_language} ({len(state.result)} chars)")
    except Exception as e:
        logger.error(f"LLM API call failed in translate node: {type(e).__name__}: {str(e)}")
        state.result = f"Error: Failed to translate to {state.target_language}. The AI service is temporarily unavailable."
        return state

    # Store to session cache
    _store_to_session_cache(state.session_id, state.query, state.result)
    
    return state

def fallback_node(state: AgentState) -> AgentState:
    """Fallback handler when query cannot be categorized.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with fallback message
    """
    logger.debug("Executing fallback node for unclassified query")
    state.result = "I didn't understand your query. Could you please rephrase it more clearly? For example, you can ask me to answer questions, summarize the video, or translate it."
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
    """Execute a query against the video using the RAG agent pipeline.
    
    Args:
        session_id: User session identifier for conversation tracking
        video_id: YouTube video ID to query against
        query: User's question or request
        
    Returns:
        Assistant's response to the query
    """
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
        logger.warning(f"Memory pruning skipped: {str(e)}")
    
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
    """Periodically clean up expired sessions (default: inactive > 1 day).
    
    Args:
        days: Number of days of inactivity before cleanup
        
    Returns:
        Number of sessions cleaned up
    """
    count = session_cache_manager.cleanup_expired_sessions(days=days)
    logger.info(f"Cleaned up {count} expired sessions")
    return count


def cleanup_expired_videos(days: int = 7) -> int:
    """Periodically clean up expired video caches (default: not accessed > 7 days).
    
    Args:
        days: Number of days of inactivity before cleanup
        
    Returns:
        Number of videos cleaned up
    """
    count = video_cache_manager.cleanup_expired_videos(days=days)
    logger.info(f"Cleaned up {count} expired video caches")
    return count


def get_video_cache_stats() -> Dict[str, Any]:
    """Get statistics about video cache usage.
    
    Returns:
        Dictionary with cache statistics (size, hit count, etc.)
    """
    return video_cache_manager.get_cache_stats()


def get_session_cache_stats() -> Dict[str, Any]:
    """Get statistics about session cache usage.
    
    Returns:
        Dictionary with cache statistics (sessions, memory usage, etc.)
    """
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
