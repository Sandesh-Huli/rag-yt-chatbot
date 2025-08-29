"""
RAG Service: Chunking, embedding, storing and retrieving transcript data.
Uses LangChain's SemanticChunker for semantic chunking and Gemini embeddings.
"""

import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import numpy as np
import faiss
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chatbot.services.transcript_service import fetch_youtube_transcript

class RAG:
    def __init__(self,chunk_size: int, chunk_overlap: int):
        load_dotenv()
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model = "models/gemini-embedding-001",
            # google_api_key=google_api_key
        )
        self.chunker = SemanticChunker(self.embedding_model)
        self.index = None
        self.chunks : List[str] = []
        self.chunk_metadata : List[Dict[str,Any]] = []

    def chunk_transcript(self, transcript: List[str]) -> List[str]: 
        """
        Uses LangChain's SemanticChunker for semantic chunking.
        """
        all_text = " ".join(transcript)
        return self.chunker.split_text(all_text)
        
    def add_transcript(self, transcript: List[str], meta: Dict[str, Any] = None):
        """
        Chunks, embeds, and stores transcript data.
        """
        chunks = self.chunk_transcript(transcript)
        # print('printing chunks \n\n\n')
        # print(chunks)
        embeddings = self.embedding_model.embed_documents(chunks)
        # print('printing embeddings \n\n\n')
        # print(embeddings)
        
        embeddings_np = np.array(embeddings).astype("float32")
        if self.index is None:
            self.index = faiss.IndexFlatL2(embeddings_np.shape[1])
        self.index.add(embeddings_np)
        self.chunks.extend(chunks)
        for _ in chunks:
            self.chunk_metadata.append(meta if meta else {})

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Embeds the query and retrieves top_k most relevant chunks.
        Returns list of dicts: {text, score, metadata}
        """
        if self.index is None or len(self.chunks) == 0:
            return []
        query_emb = np.array(self.embedding_model.embed_query(query)).astype("float32").reshape(1, -1)
        D, I = self.index.search(query_emb, top_k)
        results = []
        for idx, score in zip(I[0], D[0]):
            if idx < len(self.chunks):
                results.append({
                    "text": self.chunks[idx],
                    "score": float(score),
                    "metadata": self.chunk_metadata[idx]
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
