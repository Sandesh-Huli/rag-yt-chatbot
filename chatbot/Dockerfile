# ============================================
# Production Python FastAPI Chatbot
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements from project root (mounted via build context)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the chatbot package
COPY chatbot/ ./chatbot/

# Copy RAG store data
COPY rag_store/ ./rag_store/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

CMD ["uvicorn", "chatbot.chatbot_service:app", "--host", "0.0.0.0", "--port", "8000"]
