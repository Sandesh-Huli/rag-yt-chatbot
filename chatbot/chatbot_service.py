from fastapi import FastAPI, HTTPException
from chatbot.services.db_service import DBService
from chatbot.services.yt_agent_graph import run_query
from pydantic import BaseModel
import uuid

class NewChatRequest(BaseModel):
    video_id: str
    query: str
    
class ResumeChatRequest(BaseModel):
    # session_id: str
    video_id: str
    query: str

app = FastAPI()
db = DBService()

@app.get("/sessions")
async def list_sessions():
    return db.list_sessions()

@app.get("/sessions/{session_id}")
async def show_chats(session_id:str):
    return db.get_chat_history(session_id=session_id)

@app.post('/sessions/{session_id}')
async def resume_chat(data: ResumeChatRequest,session_id:str):
    # session_id = session_id
    video_id = data.video_id
    query = data.query
    
    response = await run_query(session_id,video_id,query)
    return {"response":response}

@app.post('/sessions')
async def new_chat(data : NewChatRequest):
    session_id = str(uuid.uuid4())
    video_id = data.video_id
    
    query = data.query
    
    response = await run_query(session_id,video_id,query)
    return {"response" : response}

@app.delete('/sessions/{session_id}')
async def delete_chat(session_id:str):
    result = db.delete_chat(session_id=session_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


    
    
    
    
    