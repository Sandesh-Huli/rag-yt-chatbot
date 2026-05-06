# ============================================
# Production Python FastAPI Chatbot
# ============================================
FROM python:3.11-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=300 \
  PIP_RETRIES=10 \
  PIP_NO_CACHE_DIR=1 \
  PIP_PROGRESS_BAR=off

# Install system dependencies needed by some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements from project root (mounted via build context)
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
  pip install --default-timeout=300 --retries=10 -r requirements.txt

# Copy the chatbot package
COPY chatbot/ ./chatbot/

RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "chatbot.chatbot_service:app", "--host", "0.0.0.0", "--port", "8000"]
