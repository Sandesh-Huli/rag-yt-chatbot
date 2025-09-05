# YouTube Chatbot with Agentic RAG

This project is an **agentic Retrieval-Augmented Generation (RAG) chatbot** for YouTube videos. It fetches video transcripts, semantically chunks and embeds them, stores them in a vector database, and uses a Large Language Model (LLM) to answer questions, summarize, or translate content—letting the LLM decide which action to take.  
**Now, chat history is also used for context and semantic retrieval, and all chatbot logic is handled in a single agent graph file.**

---

## Frameworks and Libraries Used

- **[LangChain](https://github.com/langchain-ai/langchain):** For LLM integration, text splitting, and tool abstraction.
- **[LangGraph](https://github.com/langchain-ai/langgraph):** For orchestrating the agentic workflow as a graph of nodes.
- **[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api):** To fetch YouTube video transcripts programmatically.
- **[langchain-google-genai](https://github.com/langchain-ai/langchain-google-genai):** For Gemini (Google Generative AI) LLM and embedding integration.
- **[faiss](https://github.com/facebookresearch/faiss):** For efficient vector similarity search.
- **[python-dotenv](https://github.com/theskumar/python-dotenv):** For loading environment variables from a `.env` file.
- **[nltk](https://www.nltk.org/):** For sentence tokenization (if used in chunking).
- **Standard Python libraries:** `os`, `dataclasses`, `typing`, etc.

---

## How the Chatbot Works (Summary)

1. **Transcript Fetching:**  
   The chatbot fetches the transcript for a given YouTube video using `youtube-transcript-api`.

2. **Semantic Chunking:**  
   The transcript is split into semantically meaningful chunks using LangChain's `SemanticChunker` or similar text splitter.

3. **Embedding & Storage:**  
   Each chunk is embedded using Gemini (or another supported embedding model) and stored in a FAISS vector database for fast similarity search.

4. **Retrieval:**  
   When a user asks a question, requests a summary, or asks for translation, the most relevant transcript chunks are retrieved based on semantic similarity.

5. **Chat History Context:**  
   The chatbot also retrieves and semantically searches previous chat history (Q&A) for relevant context, and includes this in the LLM prompt.

6. **Agentic Orchestration:**  
   The user's query, retrieved transcript context, and relevant chat history are passed to an LLM (Gemini).  
   The LLM acts as an agent, deciding whether to answer, summarize, or translate—by selecting the appropriate tool—based on the user's intent.

7. **Response Generation:**  
   The LLM generates a response (answer, summary, or translation) using both the transcript context, chat history, and its own knowledge, and returns it to the user.

---

## Project Structure

```
chatbot/
│
├── models/
│   └── llm.py                # LLM utility for generating responses using Gemini (Google Generative AI)
│
├── services/
│   ├── rag_service.py        # RAG service: chunking, embedding, storing, retrieving transcript & chat history
│   ├── transcript_service.py # Fetches YouTube video transcripts
│   ├── db_service.py         # Handles chat history storage and retrieval
│   └── yt_agent_graph.py     # All chatbot logic and agentic workflow using LangGraph (main entry point)
│
└── ...
```

**Note:**  
- `agent_service.py` has been removed. All chatbot logic is now in `yt_agent_graph.py`.
- The graph no longer uses a `direct_node`; all nodes have access to chat history for context.

---

## Setup

1. **Clone the repository**

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up your environment variables**

   - Create a `.env` file in the project root:
     ```
     GOOGLE_API_KEY=your-gemini-api-key-here
     ```
   - (You can use a Gemini API key or set up another supported embedding/LLM provider.)

---

## Usage

### Run the Agentic Chatbot

From the project root, run:

```sh
python -m chatbot.services.yt_agent_graph
```

You will be prompted for:
- User ID
- Session ID
- YouTube video ID
- Your query (question, summary request, or translation request)
- (If translating) Target language code (e.g., `hi` for Hindi)

The agent will:
1. Fetch the transcript
2. Chunk, embed, and store it
3. Retrieve relevant transcript chunks and relevant chat history
4. Let Gemini decide (Q&A, summarize, translate) and respond

---

## Example

```
User ID: sandesh
Session ID: s1
YouTube Video ID: jZyAB2KFDls
You: Summarize the main points of this video.

Bot: This video discusses...
```

---

## Extending

- Add new tools (e.g., sentiment analysis) by defining new node functions and registering them as tools in `yt_agent_graph.py`.
- Swap out the embedding or LLM provider by editing `rag_service.py` and `llm.py`.
- Build new workflows by composing nodes in `yt_agent_graph.py`.

---

## Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [Google Generative AI (Gemini)](https://ai.google.dev/)