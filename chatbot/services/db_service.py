from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import os

# Pydantic models
class TranscriptModel(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")
    segments: List[str] = Field(..., description="Transcript segments")
    fetched_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class MessageModel(BaseModel):
    role: str = Field(..., description="Either 'user' or 'assistant'")
    message: str = Field(..., description="The content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatHistoryModel(BaseModel):
    # user_id: str = Field(..., description="User/session identifier")
    video_id: str = Field(..., description="YouTube video ID")
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[MessageModel] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
class DBService:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["yt_chatbot"]
        self.transcripts = self.db["transcripts"]
        self.chat_history = self.db["chat_history"]
        #Indexes
        self.transcripts.create_index([("video_id", ASCENDING)], unique=True)
        self.chat_history.create_index([("video_id", ASCENDING), ("session_id", ASCENDING)], unique=True)
        self.chat_history.create_index([("last_updated", DESCENDING)])

    # Transcript methods
    def get_transcript(self, video_id: str) -> Optional[List[str]]:
        doc = self.transcripts.find_one({"video_id": video_id})
        if doc:
            transcript = TranscriptModel(**doc)
            return transcript.segments
        return None

    def save_transcript(self, video_id: str, segments: list):
        transcript = TranscriptModel(video_id=video_id, segments=segments)
        self.transcripts.update_one(
            {"video_id": video_id},
            {"$set": transcript.dict()},
            upsert=True
        )

    # Chat history methods
    def create_session(self, video_id: str, session_id: str):
        """Create a new chat session for a user"""
        chat_doc = ChatHistoryModel(
            video_id=video_id,
            session_id=session_id,
        )
        self.chat_history.insert_one(chat_doc.dict())

    def add_message(self, session_id: str,video_id:str, role: str, message: str):
        """Append a message to an existing chat session"""
        msg = MessageModel(role=role, message=message).dict()
        self.chat_history.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": msg},
                "$setOnInsert": {
                    "session_id": session_id,
                    "video_id":video_id,
                    "created_at": datetime.utcnow(),
                },
                "$set": {"last_updated": datetime.utcnow()},
            },
            upsert=True,
        )

    def get_chat_history(self, session_id: str):
        """Get full chat history for a session"""
        # doc = self.chat_history.find_one({"video_id": video_id, "session_id": session_id})
        doc = self.chat_history.find_one({"session_id": session_id})
        if not doc:
            return None
        return ChatHistoryModel(**doc)
    
    def list_sessions(self):
        """List all chat sessions for a user, sorted by last_updated"""
        docs = self.chat_history.find({}).sort("last_updated",DESCENDING)
        return [
            {
                "session_id":d["session_id"],
                "video_id":d["video_id"],
                "last_updated":d["last_updated"],
                "created_at":d["created_at"],
            } for d in docs
        ]
    
    def delete_chat(self,session_id:str):
        """Delete all chat history for a particular session"""
        result = self.chat_history.delete_many({"session_id":session_id})
        return result
        

