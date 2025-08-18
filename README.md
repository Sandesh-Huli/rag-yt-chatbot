# YouTube Chatbot with LangChain & Gemini

This project is a conversational AI chatbot that answers questions about YouTube videos using their transcripts. It leverages [LangChain](https://github.com/langchain-ai/langchain), Google Gemini models, and FAISS vector search.

## Features

- Fetches YouTube video transcripts automatically
- Splits transcripts into manageable chunks
- Embeds text using Google Gemini embeddings
- Stores and searches chunks using FAISS vector store
- Answers user questions using a Gemini LLM, grounded in the video transcript

## Setup

1. **Clone the repository**

2. **Install dependencies**

   ```sh
   pip install -r requirements.txt
   ```

3. **Set up your API key**

   Create a `.env` file in the project root:

   ```
   GOOGLE_API_KEY="your-google-api-key"
   ```

4. **Run the notebook**

   Open `Main.ipynb` in VS Code or Jupyter and run the cells.

## Usage

- The notebook fetches the transcript for a given YouTube video ID.
- It processes the transcript, creates embeddings, and builds a vector store.
- You can ask questions about the video, and the chatbot will answer using only the transcript context.

## File Structure

- [`Main.ipynb`](Main.ipynb): Main notebook with all code and logic
- `.env`: Stores your Google API key (not to be shared)
- `README.md`: Project documentation

## Requirements

- Python 3.8+
- Google Gemini API access
- See `requirements.txt` for Python dependencies

## Credits

- [LangChain](https://github.com/langchain-ai/langchain)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- Google Gemini

---
