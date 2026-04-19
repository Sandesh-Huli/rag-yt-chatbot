"""
Centralized configuration for YouTube Chatbot RAG pipeline.
All environment variables and configuration values should be managed here.
"""

import os
from dotenv import load_dotenv
from chatbot.logging_config import setup_structured_logging, get_logger

# Setup structured logging (Issue 40)
logger = setup_structured_logging("yt-chatbot")

# Load environment variables ONCE at module import time
load_dotenv()

# ============== DATABASE CONFIGURATION ==============
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/chatbot')
MONGO_MAX_POOL_SIZE = int(os.getenv('MONGO_MAX_POOL_SIZE', '50'))
MONGO_MIN_POOL_SIZE = int(os.getenv('MONGO_MIN_POOL_SIZE', '10'))
MONGO_WAIT_QUEUE_TIMEOUT = int(os.getenv('MONGO_WAIT_QUEUE_TIMEOUT', '10000'))
MONGO_SERVER_SELECTION_TIMEOUT = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT', '5000'))

# ============== API KEYS & AUTHENTICATION ==============
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # For Gemini LLM
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')  # For Custom Search API
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
JWT_SECRET = os.getenv('JWT_SECRET')
SESSION_SECRET = os.getenv('SESSION_SECRET')

# Validate secrets at startup
if JWT_SECRET and len(JWT_SECRET) < 32:
    logger.warning("JWT_SECRET is less than 32 characters (not recommended for production)")
if SESSION_SECRET and len(SESSION_SECRET) < 32:
    logger.warning("SESSION_SECRET is less than 32 characters (not recommended for production)")

# ============== CORS CONFIGURATION ==============
CORS_ORIGINS_STR = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:5173,http://localhost:5174,http://localhost:5175'
)
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(',')]

# ============== LLM CONFIGURATION ==============
LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-2.5-flash')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0'))  # Deterministic responses
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))

# ============== RAG CONFIGURATION ==============
RETRIEVAL_TOP_K = int(os.getenv('RETRIEVAL_TOP_K', '3'))  # Number of chunks to retrieve
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))  # Characters per chunk
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))  # Overlap between chunks

# ============== CACHE CONFIGURATION ==============
VIDEO_CACHE_TTL = int(os.getenv('VIDEO_CACHE_TTL', '3600'))  # 1 hour in seconds
SESSION_CACHE_TTL = int(os.getenv('SESSION_CACHE_TTL', '86400'))  # 24 hours in seconds
MAX_CHAT_HISTORY = int(os.getenv('MAX_CHAT_HISTORY', '50'))  # Max messages per session

# ============== SESSION CONFIGURATION ==============
SESSION_MAX_AGE = int(os.getenv('SESSION_MAX_AGE', str(1000 * 60 * 60 * 24 * 7)))  # 1 week in ms
SESSION_SECURE = os.getenv('SESSION_SECURE', 'false').lower() == 'true'  # HTTPS only
SESSION_SAME_SITE = os.getenv('SESSION_SAME_SITE', 'lax')  # csrf protection

# ============== LOGGING CONFIGURATION ==============
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ============== FEATURE FLAGS ==============
ENABLE_WEB_SEARCH = os.getenv('ENABLE_WEB_SEARCH', 'true').lower() == 'true'
ENABLE_TRANSLATION = os.getenv('ENABLE_TRANSLATION', 'true').lower() == 'true'
ENABLE_SUMMARIZATION = os.getenv('ENABLE_SUMMARIZATION', 'true').lower() == 'true'

# ============== VALIDATION ==============
QUERY_MAX_LENGTH = int(os.getenv('QUERY_MAX_LENGTH', '5000'))
QUERY_MIN_LENGTH = int(os.getenv('QUERY_MIN_LENGTH', '1'))
ORCHESTRATOR_QUERY_MAX_LENGTH = int(os.getenv('ORCHESTRATOR_QUERY_MAX_LENGTH', '1000'))

# Required variables validation
required_vars = ['MONGO_URI', 'GOOGLE_API_KEY', 'GOOGLE_SEARCH_KEY', 'GOOGLE_CSE_ID', 'CORS_ORIGINS', 'JWT_SECRET', 'SESSION_SECRET']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f'❌ Missing required environment variables: {", ".join(missing_vars)}')
    logger.error('Please check your .env file and refer to .env.example')
    # Don't exit here - let the application handle it
else:
    logger.info('✅ All required configuration variables loaded successfully')
