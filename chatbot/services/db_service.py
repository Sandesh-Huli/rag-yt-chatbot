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

class UserModel(BaseModel):
    email: str = Field(..., description="User email (unique)")
    username: str = Field(..., description="Username")
    hashed_password: str = Field(..., description="Hashed password")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class ChatHistoryModel(BaseModel):
    user_id: Optional[str] = Field(None, description="User identifier")
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
        self.users = self.db["users"]
        #Indexes
        self.transcripts.create_index([("video_id", ASCENDING)], unique=True)
        self.chat_history.create_index([("session_id", ASCENDING)], unique=True)
        self.chat_history.create_index([("user_id", ASCENDING), ("last_updated", DESCENDING)])
        self.users.create_index([("email", ASCENDING)], unique=True)

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
    def create_session(self, video_id: str, session_id: str, user_id: str = None):
        """Create a new chat session for a user"""
        chat_doc = ChatHistoryModel(
            video_id=video_id,
            session_id=session_id,
            user_id=user_id,
        )
        self.chat_history.insert_one(chat_doc.dict())

    def add_message(self, session_id: str, video_id: str, role: str, message: str, user_id: str = None):
        """Append a message to an existing chat session"""
        msg = MessageModel(role=role, message=message).dict()
        update_data = {
            "$push": {"messages": msg},
            "$setOnInsert": {
                "session_id": session_id,
                "video_id": video_id,
                "created_at": datetime.utcnow(),
            },
            "$set": {"last_updated": datetime.utcnow()},
        }
        if user_id:
            update_data["$setOnInsert"]["user_id"] = user_id
        
        self.chat_history.update_one(
            {"session_id": session_id},
            update_data,
            upsert=True,
        )

    def get_chat_history(self, session_id: str, user_id: str = None):
        """Get full chat history for a session"""
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        
        doc = self.chat_history.find_one(query)
        if not doc:
            return None
        return ChatHistoryModel(**doc)
    
    def list_sessions(self, user_id: str = None):
        """List all chat sessions for a user, sorted by last_updated"""
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        docs = self.chat_history.find(query).sort("last_updated", DESCENDING)
        return [
            {
                "session_id": d["session_id"],
                "video_id": d["video_id"],
                "last_updated": d["last_updated"],
                "created_at": d.get("created_at"),
                "user_id": d.get("user_id"),
            } for d in docs
        ]
    
    def delete_chat(self, session_id: str, user_id: str = None):
        """Delete all chat history for a particular session"""
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        
        result = self.chat_history.delete_many(query)
        return result
    
    # User methods
    def create_user(self, email: str, username: str, hashed_password: str):
        """Create a new user account"""
        user = UserModel(
            email=email,
            username=username,
            hashed_password=hashed_password
        )
        result = self.users.insert_one(user.dict())
        return str(result.inserted_id)
    
    def get_user_by_email(self, email: str):
        """Get user by email"""
        doc = self.users.find_one({"email": email})
        if doc:
            return UserModel(**doc)
        return None
    
    def get_user_by_id(self, user_id: str):
        """Get user by ID"""
        from bson import ObjectId
        try:
            doc = self.users.find_one({"_id": ObjectId(user_id)})
            if doc:
                return UserModel(**doc)
        except:
            pass
        return None
        

