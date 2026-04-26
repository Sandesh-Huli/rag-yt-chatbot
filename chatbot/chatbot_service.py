from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from chatbot.services.db_service import DBService
from chatbot.services.yt_agent_graph import run_query
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from chatbot.models.validators import (
    validate_video_id,
    validate_query,
    validate_user_id,
    validate_session_id,
)
import uuid
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate required environment variables
required_env_vars = [
    'MONGO_URI',
    'GOOGLE_API_KEY',
    'GOOGLE_SEARCH_KEY',
    'GOOGLE_CSE_ID',
    'CORS_ORIGINS',
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    logger.error('❌ Error: Missing required environment variables:')
    for var in missing_vars:
        logger.error(f'   - {var}')
    logger.error('\nPlease check your .env file and ensure all required variables are set.')
    logger.error('Refer to .env.example for the required configuration.\n')
    sys.exit(1)

logger.info('✅ Environment variables validated successfully')

# Additional startup validation for security
jwt_secret = os.getenv('JWT_SECRET', '')
if len(jwt_secret) < 32:
    logger.error('❌ Error: JWT_SECRET must be at least 32 characters long')
    logger.error('   Generate a strong secret with: python -c "import secrets; print(secrets.token_urlsafe(32))"')
    sys.exit(1)

session_secret = os.getenv('SESSION_SECRET', '')
if len(session_secret) < 32:
    logger.error('❌ Error: SESSION_SECRET must be at least 32 characters long')
    logger.error('   Generate a strong secret with: python -c "import secrets; print(secrets.token_urlsafe(32))"')
    sys.exit(1)

logger.info('✅ Security validation passed: JWT and session secrets are strong')

class NewChatRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID (11 characters)")
    query: str = Field(..., min_length=1, max_length=5000, description="User query (1-5000 characters)")
    user_id: Optional[str] = Field(None, description="User ID (MongoDB ObjectId or UUID)")
    
    @field_validator('video_id')
    @classmethod
    def validate_vid_id(cls, v: str) -> str:
        return validate_video_id(v)
    
    @field_validator('query')
    @classmethod
    def validate_q(cls, v: str) -> str:
        return validate_query(v)
    
    @field_validator('user_id')
    @classmethod
    def validate_uid(cls, v: Optional[str]) -> Optional[str]:
        return validate_user_id(v)
    
class ResumeChatRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID (11 characters)")
    query: str = Field(..., min_length=1, max_length=5000, description="User query (1-5000 characters)")
    user_id: Optional[str] = Field(None, description="User ID (MongoDB ObjectId or UUID)")
    
    @field_validator('video_id')
    @classmethod
    def validate_vid_id(cls, v: str) -> str:
        return validate_video_id(v)
    
    @field_validator('query')
    @classmethod
    def validate_q(cls, v: str) -> str:
        return validate_query(v)
    
    @field_validator('user_id')
    @classmethod
    def validate_uid(cls, v: Optional[str]) -> Optional[str]:
        return validate_user_id(v)

app = FastAPI()

# Health check endpoint for Docker/K8s probes (Blocker 2)
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "chatbot"}

# Parse CORS origins from environment variable
cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:5175')
cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

db = DBService()

logger.info('🚀 FastAPI chatbot service initialized')
logger.info(f'✅ CORS configured for origins: {cors_origins}')
# Safe logging - don't log credentials
mongo_uri = os.getenv('MONGO_URI', '')
mongo_safe = f"mongodb://{mongo_uri.split('://')[-1][:20]}..." if mongo_uri else 'Not set'
logger.info(f'📊 Database connection: {mongo_safe}')

@app.get("/chats/sessions")
async def list_sessions(user_id: Optional[str] = None):
    try:
        if user_id:
            validate_user_id(user_id)
        sessions = db.list_sessions(user_id=user_id)
        logger.info(f"Listed {len(sessions)} sessions for user: {user_id}")
        return sessions
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/chats/sessions/{session_id}")
async def show_chats(session_id: str, user_id: Optional[str] = None):
    try:
        validate_session_id(session_id)
        if user_id:
            validate_user_id(user_id)
        session = db.get_chat_history(session_id=session_id, user_id=user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        logger.info(f"Retrieved session: {session_id} for user: {user_id}")
        return session
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post('/chats/sessions/{session_id}')
async def resume_chat(session_id: str, data: ResumeChatRequest):
    try:
        validate_session_id(session_id)
        # Data is already validated by Pydantic model
        logger.info(f"Resume chat - Session: {session_id}, Video: {data.video_id[:11]}, User: {data.user_id}")
        
        # Check if session exists and belongs to user
        existing = db.get_chat_history(session_id=session_id, user_id=data.user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        
        response = run_query(session_id, data.video_id, data.query)
        logger.info(f"Response generated for session {session_id}")
        return {"response": response}
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in resume_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post('/chats/sessions')
async def new_chat(data: NewChatRequest):
    try:
        session_id = str(uuid.uuid4())
        logger.info(f"New chat - Session: {session_id}, Video: {data.video_id[:11]}, User: {data.user_id}")
        
        # Always create session with user_id to ensure it's stored in DB (Issue: fix)
        db.create_session(video_id=data.video_id, session_id=session_id, user_id=data.user_id)
        
        response = run_query(session_id, data.video_id, data.query)
        logger.info(f"Response generated for session {session_id}")
        return {
            "session_id": session_id,
            "response": response
        }
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in new_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete('/chats/sessions/{session_id}')
async def delete_chat(session_id: str, user_id: Optional[str] = None):
    try:
        validate_session_id(session_id)
        if user_id:
            validate_user_id(user_id)
        result = db.delete_chat(session_id=session_id, user_id=user_id)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        logger.info(f"Deleted session: {session_id} for user: {user_id}")
        return {"message": "Session deleted"}
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Entry point for container execution (Blocker 1)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )