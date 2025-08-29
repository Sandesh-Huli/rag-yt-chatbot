from chatbot.services.transcript_service import fetch_youtube_transcript
from chatbot.models.llm import get_llm_response
from chatbot.services.rag_service import RAG
from dotenv import load_dotenv
from typing import Any, List, Dict

SYS_PROMPT = """You are a helpful YouTube assistant.
- Use transcript when available.
- If transcript doesn’t have enough, use your own knowledge.
- Always answer simply and clearly.
- Include timestamps if relevant.
"""

def _format_context_with_timestamps(chunks: List[Dict[str, Any]]) -> str:
    """Create a readable context block that preserves any available timestamps."""
    formatted = []
    for c in chunks:
        ts = ""
        meta = c.get("metadata") or {}
        start = meta.get("start") or c.get("start")
        if start is not None:
            try:
                sec = int(float(start))
                mm = sec // 60
                ss = sec % 60
                ts = f"[{mm:02d}:{ss:02d}] "
            except Exception:
                ts = ""
        formatted.append(f"{ts}{c.get('text','')}".strip())
    return "\n".join(formatted)

class Chatbot:
    def __init__(self, chunk_size: int = 100, chunk_overlap: int = 30):
        load_dotenv()
        self.rag = RAG(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.video_id = None
        self.transcript_segments: List[str] = []

    # Node 1: Fetch transcript
    def fetch_transcript_node(self, video_id: str, lang: str = "en") -> List[str]:
        self.video_id = video_id
        self.transcript_segments = fetch_youtube_transcript(video_id, lang=lang)
        return self.transcript_segments

    # Node 2: Add transcript to RAG
    def add_transcript_node(self, meta: Dict[str, Any] = None) -> None:
        if not self.transcript_segments:
            raise RuntimeError("No transcript loaded. Please fetch transcript first.")
        self.rag.add_transcript(self.transcript_segments, meta=meta or {"video_id": self.video_id})

    # Node 3: Retrieve relevant chunks
    def retrieve_chunks_node(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.transcript_segments:    
            raise RuntimeError("No transcript loaded. Please fetch transcript first.")
        return self.rag.retrieve(query, top_k=top_k)

    # Node 4a: Q&A node
    def qa_node(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        context = _format_context_with_timestamps(retrieved_chunks)
        prompt = (
            f"{SYS_PROMPT}\n\n"
            f"Task: Answer the user's question using the transcript context when helpful.\n"
            f"If the transcript is insufficient, use your own knowledge to fill gaps.\n\n"
            f"Transcript Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Answer (clear and simple):"
        )
        return get_llm_response(prompt)

    # Node 4b: Summarize node
    def summarize_node(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        context = _format_context_with_timestamps(retrieved_chunks)
        prompt = (
            f"{SYS_PROMPT}\n\n"
            f"Task: Summarize the following transcript context in a concise, beginner-friendly paragraph. "
            f"If helpful, include rough timestamps.\n\n"
            f"Transcript Context:\n{context}\n\n"
            f"Summary:"
        )
        return get_llm_response(prompt)

    # Node 4c: Translate node
    def translate_node(self, retrieved_chunks: List[Dict[str, Any]], target_language: str = "en") -> str:
        context = _format_context_with_timestamps(retrieved_chunks)
        prompt = (
            f"{SYS_PROMPT}\n\n"
            f"Task: Translate the following transcript context to {target_language}. Preserve meaning and any inline timestamps.\n\n"
            f"Transcript Context:\n{context}\n\n"
            f"Translation ({target_language}):"
        )
        return get_llm_response(prompt, target_language=target_language)