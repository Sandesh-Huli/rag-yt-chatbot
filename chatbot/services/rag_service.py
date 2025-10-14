"""
RAG Service: Chunking, embedding, storing and retrieving transcript & chat history.
Uses LangChain's SemanticChunker for semantic chunking and Gemini embeddings.
"""

import os
import pickle
from dotenv import load_dotenv
from typing import List, Dict, Any
import numpy as np
import faiss
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chatbot.services.transcript_service import fetch_youtube_transcript

class RAG:
    def __init__(self,chunk_size: int =100 , chunk_overlap: int = 30, persist_dir: str = "./rag_store"):
        load_dotenv()
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model = "models/gemini-embedding-001",
            # google_api_key=google_api_key
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
        chunks = self.chunk_transcript(transcript)
        embeddings = self.embedding_model.embed_documents(chunks)
        
        embeddings_np = np.array(embeddings).astype("float32")
        if self.transcript_index is None:
            self.transcript_index = faiss.IndexFlatL2(embeddings_np.shape[1])
        self.transcript_index.add(embeddings_np)
        self.transcript_chunks.extend(chunks)
        for _ in chunks:
            self.transcript_metadata.append(meta if meta else {})

    def retrieve_transcript(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top_k transcript chunks relevant to query."""
        if self.transcript_index is None or len(self.transcript_chunks) == 0:
            return []
        if isinstance(top_k, list):
            # if accidentally passed as [5] or ["5"]
            top_k = int(top_k[0])
        else:
            top_k = int(top_k)
            
        print("DEBUG top_k type:", type(top_k), "value:", top_k)

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

    def add_query(self, query: str, meta: Dict[str, Any] = None):
        """Embeds and stores chat history messages (user or assistant)."""
        emb = self.embedding_model.embed_query(query)
        emb_np = np.array(emb).astype("float32").reshape(1, -1)

        if self.query_index is None:
            self.query_index = faiss.IndexFlatL2(emb_np.shape[1])

        self.query_index.add(emb_np)
        self.query_texts.append(query)
        self.query_metadata.append(meta if meta else {})

    def retrieve_queries(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve semantically relevant chat history messages."""
        if self.query_index is None or len(self.query_texts) == 0:
            print('valag bande')
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
    results = rag.retrieve(query=query, top_k=2)
    print("Top results:")
    for res in results:
        print("-", res["text"], "| Score:", res["score"])
    chunked_data = rag.chunk_transcript(transcript_segments)
    print(chunked_data)
