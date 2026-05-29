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
# COPY requirements.txt .
# RUN python -m pip install --upgrade pip setuptools wheel && \
#   pip install --default-timeout=300 --retries=10 -r requirements.txt
COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --upgrade pip setuptools wheel && \
  pip install --default-timeout=300 --retries=10 -r requirements.txt

# Copy the chatbot package
COPY chatbot/ ./chatbot/

RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

# Health check: verify the service is responding to requests
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 8000)); s.close()" || exit 1

CMD ["uvicorn", "chatbot.chatbot_service:app", "--host", "0.0.0.0", "--port", "8000"]
