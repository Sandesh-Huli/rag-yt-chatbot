from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from chatbot.services.db_service import DBService
from chatbot.services.yt_agent_graph import run_query
from pydantic import BaseModel
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
    'GOOGLE_CSE_ID'
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

class NewChatRequest(BaseModel):
    video_id: str
    query: str
    user_id: str = None
    
class ResumeChatRequest(BaseModel):
    video_id: str
    query: str
    user_id: str = None

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DBService()

logger.info('🚀 FastAPI chatbot service initialized')
logger.info(f'📊 MongoDB URI: {os.getenv("MONGO_URI")}')

@app.get("/chats/sessions")
async def list_sessions(user_id: str = None):
    try:
        sessions = db.list_sessions(user_id=user_id)
        logger.info(f"Listed {len(sessions)} sessions for user: {user_id}")
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chats/sessions/{session_id}")
async def show_chats(session_id: str, user_id: str = None):
    try:
        session = db.get_chat_history(session_id=session_id, user_id=user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        logger.info(f"Retrieved session: {session_id} for user: {user_id}")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chats/sessions/{session_id}')
async def resume_chat(session_id: str, data: ResumeChatRequest):
    try:
        logger.info(f"Resume chat - Session: {session_id}, Video: {data.video_id}, Query: {data.query}, User: {data.user_id}")
        
        # Check if session exists and belongs to user
        existing = db.get_chat_history(session_id=session_id, user_id=data.user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        
        response = run_query(session_id, data.video_id, data.query)
        logger.info(f"Response generated for session {session_id}")
        return {"response": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in resume_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chats/sessions')
async def new_chat(data: NewChatRequest):
    try:
        session_id = str(uuid.uuid4())
        logger.info(f"New chat - Session: {session_id}, Video: {data.video_id}, Query: {data.query}, User: {data.user_id}")
        
        # Create session with user_id if provided
        if data.user_id:
            db.create_session(video_id=data.video_id, session_id=session_id, user_id=data.user_id)
        
        response = run_query(session_id, data.video_id, data.query)
        logger.info(f"Response generated for session {session_id}")
        return {
            "session_id": session_id,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error in new_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete('/chats/sessions/{session_id}')
async def delete_chat(session_id: str, user_id: str = None):
    try:
        result = db.delete_chat(session_id=session_id, user_id=user_id)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        logger.info(f"Deleted session: {session_id} for user: {user_id}")
        return {"message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


    
    
    
    
    