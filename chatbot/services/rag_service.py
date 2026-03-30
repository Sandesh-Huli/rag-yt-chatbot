"""
RAG Service: Chunking, embedding, storing and retrieving transcript & chat history.
Uses LangChain's SemanticChunker for semantic chunking and Gemini embeddings.
"""

import os
import pickle
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)
import faiss
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from chatbot.services.transcript_service import fetch_youtube_transcript

class RAG:
    def __init__(self, persist_dir: str = "./rag_store"):
        load_dotenv()
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        # transcript index
        self.transcript_chunker = SemanticChunker(self.embedding_model)
        self.transcript_index = None
        self.transcript_chunks: List[str] = []
        self.transcript_metadata: List[Dict[str, Any]] = []

        # query (chat history) index
        self.query_index = None
        self.query_texts: List[str] = []
        self.query_metadata: List[Dict[str, Any]] = []

        # try load from disk
        self._load_indexes()
        
    # -------------------- Persistence Helpers --------------------
    def _save_indexes(self):
        # transcript
        if self.transcript_index:
            faiss.write_index(self.transcript_index, os.path.join(self.persist_dir, "transcript.index"))
            with open(os.path.join(self.persist_dir, "transcript.pkl"), "wb") as f:
                pickle.dump((self.transcript_chunks, self.transcript_metadata), f)

        # queries
        if self.query_index:
            faiss.write_index(self.query_index, os.path.join(self.persist_dir, "query.index"))
            with open(os.path.join(self.persist_dir, "query.pkl"), "wb") as f:
                pickle.dump((self.query_texts, self.query_metadata), f)

    def _load_indexes(self):
        try:
            # transcript
            if os.path.exists(os.path.join(self.persist_dir, "transcript.index")):
                self.transcript_index = faiss.read_index(os.path.join(self.persist_dir, "transcript.index"))
                with open(os.path.join(self.persist_dir, "transcript.pkl"), "rb") as f:
                    self.transcript_chunks, self.transcript_metadata = pickle.load(f)

            # queries
            if os.path.exists(os.path.join(self.persist_dir, "query.index")):
                self.query_index = faiss.read_index(os.path.join(self.persist_dir, "query.index"))
                with open(os.path.join(self.persist_dir, "query.pkl"), "rb") as f:
                    self.query_texts, self.query_metadata = pickle.load(f)
        except Exception as e:
            print("⚠️ Failed to load FAISS indexes:", e)
    
    def is_video_indexed(self, video_id: str) -> bool:
        """Check if a video_id is already indexed in transcript metadata."""
        for metadata in self.transcript_metadata:
            if metadata.get("video_id") == video_id:
                return True
        return False
        
    def chunk_transcript(self, transcript: List[str]) -> List[str]: 
        """
        Uses LangChain's SemanticChunker for semantic chunking.
        """
        all_text = " ".join(transcript)
        return self.transcript_chunker.split_text(all_text)
        
    def add_transcript(self, transcript: List[str], meta: Dict[str, Any] = None):
        """
        Chunks, embeds, and stores transcript data.
        """
        try:
            chunks = self.chunk_transcript(transcript)
            embeddings = self.embedding_model.embed_documents(chunks)
            
            embeddings_np = np.array(embeddings).astype("float32")
            if self.transcript_index is None:
                self.transcript_index = faiss.IndexFlatL2(embeddings_np.shape[1])
            self.transcript_index.add(embeddings_np)
            self.transcript_chunks.extend(chunks)
            for _ in chunks:
                self.transcript_metadata.append(meta if meta else {})
            self._save_indexes()
        except Exception as e:
            raise RuntimeError(f"Error adding transcript to RAG: {str(e)}")
        
        # Print embedding vectors to console
        print("\n" + "="*80)
        print("📊 TRANSCRIPT EMBEDDING VECTORS GENERATED")
        print("="*80)
        print(f"Embedding Model: sentence-transformers/all-mpnet-base-v2")
        print(f"Total Chunks: {len(chunks)}")
        print(f"Vector Dimensions: {embeddings_np.shape[1]}")
        print(f"Metadata: {meta}")
        print("\n" + "-"*80)
        
        # Print first 3 embeddings (for readability)
        num_to_print = min(3, len(chunks))
        for i in range(num_to_print):
            print(f"\n📄 Chunk {i+1}/{len(chunks)}:")
            print(f"Text: \"{chunks[i][:100]}{'...' if len(chunks[i]) > 100 else ''}\"")
            print(f"\nVector (first 20 dimensions):")
            vector_sample = embeddings_np[i][:20]
            for j in range(0, 20, 5):
                formatted = ", ".join([f"{v:7.4f}" for v in vector_sample[j:j+5]])
                print(f"  [{j:2d}-{j+4:2d}]: {formatted}")
            
            print(f"\nVector Statistics:")
            print(f"  Min:  {np.min(embeddings_np[i]):8.4f}")
            print(f"  Max:  {np.max(embeddings_np[i]):8.4f}")
            print(f"  Mean: {np.mean(embeddings_np[i]):8.4f}")
            print(f"  Std:  {np.std(embeddings_np[i]):8.4f}")
            print(f"  Norm: {np.linalg.norm(embeddings_np[i]):8.4f}")
            
            if i < num_to_print - 1:
                print("\n" + "-"*80)
        
        if len(chunks) > num_to_print:
            print(f"\n... ({len(chunks) - num_to_print} more chunks embedded)")
        
        print("\n" + "="*80)
        print(f"✅ All {len(chunks)} embeddings stored in FAISS index")
        print("="*80 + "\n")

    def retrieve_transcript(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top_k transcript chunks relevant to query."""
        try:
            if self.transcript_index is None or len(self.transcript_chunks) == 0:
                return []
            if isinstance(top_k, list):
                # if accidentally passed as [5] or ["5"]
                top_k = int(top_k[0])
            else:
                top_k = int(top_k)

            query_emb = np.array(self.embedding_model.embed_query(query)).astype("float32").reshape(1, -1)
            D, I = self.transcript_index.search(query_emb, top_k)
            results = []
            for idx, score in zip(I[0], D[0]):
                if idx < len(self.transcript_chunks):
                    results.append({
                        "text": self.transcript_chunks[idx],
                        "score": float(score),
                        "metadata": self.transcript_metadata[idx]
                    })
            return results
        except Exception as e:
            logger.error(f"Error retrieving transcript: {str(e)}")
            return []

    def add_query(self, query: str, meta: Dict[str, Any] = None):
        """Embeds and stores chat history messages (user or assistant)."""
        emb = self.embedding_model.embed_query(query)
        emb_np = np.array(emb).astype("float32").reshape(1, -1)
        if self.query_index is None:
            self.query_index = faiss.IndexFlatL2(emb_np.shape[1])

        self.query_index.add(emb_np)
        self.query_texts.append(query)
        self.query_metadata.append(meta if meta else {})

    def check_and_prune_memory(self, db_service, session_id: str, video_id: str, 
                               max_messages: int = 15, summary_threshold: int = 20):
        """
        Check if chat memory exceeds threshold and prune/summarize old messages.
        Only summarizes ORIGINAL messages (is_original=True), never re-summarizes.
        """
        try:
            from chatbot.models.llm import get_llm_response
            from datetime import datetime
            
            message_count = len(self.query_texts)
            
            # If total messages exceed summary threshold
            if message_count > summary_threshold:
                # Get original messages from DB
                original_msgs = db_service.get_original_messages(session_id, from_index=0)
                
                if original_msgs and len(original_msgs) > max_messages:
                    # Extract messages to summarize (first N-max_messages indices)
                    messages_to_summarize = original_msgs[:len(original_msgs) - max_messages]
                    
                    # Build text for LLM summarization (only original messages)
                    text_to_summarize = "\n".join([
                        f"{role}: {msg.get('message', '')}" 
                        for idx, msg in messages_to_summarize
                        for role in [msg.get('role', 'unknown')]
                        if msg.get('is_original', True)
                    ])
                    
                    if text_to_summarize.strip():
                        # Summarize using LLM
                        try:
                            summary_prompt = f"Briefly summarize this conversation in 2-3 sentences:\n\n{text_to_summarize}"
                            summary = get_llm_response(summary_prompt)
                            summary_text = summary.content if hasattr(summary, "content") else str(summary)
                            
                            # Get indices of messages to delete
                            indices_to_delete = [idx for idx, _ in messages_to_summarize]
                            
                            # Save summary to DB and mark as non-original
                            db_service.mark_message_as_summary(
                                session_id, 
                                f"[SUMMARY] {summary_text}", 
                                indices_to_delete
                            )
                            
                            # Delete old messages from DB
                            db_service.delete_messages_by_index(session_id, indices_to_delete)
                            
                            # Update memory state
                            memory_state = {
                                "conversation_summary": summary_text,
                                "total_messages_processed": message_count,
                                "active_window_start_index": len(messages_to_delete),
                                "last_summarization_index": max(indices_to_delete) if indices_to_delete else 0,
                                "last_summarized_at": datetime.utcnow()
                            }
                            db_service.save_memory_state(session_id, video_id, memory_state)
                            
                            logger.info(f"✅ Summarized {len(messages_to_summarize)} original messages, keeping last {max_messages}")
                        except Exception as e:
                            logger.error(f"Error during summarization: {str(e)}")
            
            # Return current memory state
            return db_service.get_memory_state(session_id, video_id)
            
        except Exception as e:
            logger.error(f"Error in check_and_prune_memory: {str(e)}")
            return None

    def retrieve_queries(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve semantically relevant chat history messages."""
        if self.query_index is None or len(self.query_texts) == 0:
            return []
        query_emb = np.array(self.embedding_model.embed_query(query)).astype("float32").reshape(1, -1)
        D, I = self.query_index.search(query_emb, top_k)
        results = []
        for idx, score in zip(I[0], D[0]):
            if idx < len(self.query_texts):
                results.append({
                    "text": self.query_texts[idx],
                    "score": float(score),
                    "metadata": self.query_metadata[idx]
                })
                
        return results


# Example usage
if __name__ == "__main__":
    video_id = input('Give video id here: ')
    transcript_segments = fetch_youtube_transcript(video_id=video_id)
    rag = RAG()
    rag.add_transcript(transcript_segments, meta={"video_id": video_id})
    query = input('Enter your query here: ')
    results = rag.retrieve_queries(query=query, top_k=2)
    print("Top results:")
    for res in results:
        print("-", res["text"], "| Score:", res["score"])
    chunked_data = rag.chunk_transcript(transcript_segments)
    print(chunked_data)
