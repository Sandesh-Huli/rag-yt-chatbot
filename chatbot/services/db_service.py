from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import os
import threading

from chatbot.logging_config import get_logger

logger = get_logger(__name__)


# ============= MongoDB Singleton Connection Pool =============
class MongoDBClientSingleton:
    """
    Thread-safe singleton for MongoDB connection pooling.
    Ensures only one MongoClient instance is created and reused across the application.
    
    Configuration:
    - maxPoolSize=50: Handle up to 50 concurrent requests
    - minPoolSize=10: Keep 10 idle connections ready
    - waitQueueTimeoutMS=10000: Timeout for connection queue
    - serverSelectionTimeoutMS=5000: Initial connection timeout
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize MongoDB connection once."""
        try:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            
            # Connection pool configuration
            self.client = MongoClient(
                mongo_uri,
                maxPoolSize=50,              # Max concurrent connections
                minPoolSize=10,              # Min idle connections
                waitQueueTimeoutMS=10000,    # Queue timeout
                serverSelectionTimeoutMS=5000,  # Connection timeout
                retryWrites=True,            # Automatic retry on transient errors
                w=1,                         # Write concern
            )
            
            # Verify connection
            self.client.admin.command('ping')
            logger.info("MongoDB connection pool initialized", {
                "event_type": "db_connection_pool_init",
                "max_pool_size": 50,
                "min_pool_size": 10,
                "connection_timeout_ms": 5000,
                "wait_queue_timeout_ms": 10000,
            })
            
        except Exception as e:
            logger.error("Failed to initialize MongoDB connection", {
                "event_type": "db_connection_error",
                "error": str(e),
                "mongo_uri_set": bool(os.getenv("MONGO_URI")),
            })
            raise
    
    def get_client(self) -> MongoClient:
        """Get the MongoDB client instance."""
        return self.client
    
    def disconnect(self):
        """Gracefully disconnect from MongoDB."""
        if self.client:
            try:
                self.client.close()
                logger.info("MongoDB connection pool closed", {
                    "event_type": "db_connection_closed",
                })
            except Exception as e:
                logger.error("Error closing MongoDB connection", {
                    "event_type": "db_disconnect_error",
                    "error": str(e),
                })


# Global singleton instance
_mongo_singleton = MongoDBClientSingleton()


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
        # Use singleton MongoDB connection pool instead of creating new clients
        self.client = _mongo_singleton.get_client()
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
                "last_updated": d["last_updated"].isoformat() if d.get("last_updated") else None,
                "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
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

    # Memory Management Methods (for conversation summarization & sliding window)
    def save_memory_state(self, session_id: str, video_id: str, memory_state: dict):
        """Save memory window state and conversation summary"""
        self.chat_history.update_one(
            {"session_id": session_id, "video_id": video_id},
            {
                "$set": {
                    "memory_state": {
                        "conversation_summary": memory_state.get("conversation_summary", ""),
                        "total_messages_processed": memory_state.get("total_messages_processed", 0),
                        "active_window_start_index": memory_state.get("active_window_start_index", 0),
                        "last_summarization_index": memory_state.get("last_summarization_index", 0),
                        "last_summarized_at": memory_state.get("last_summarized_at", datetime.utcnow())
                    },
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    def get_memory_state(self, session_id: str, video_id: str):
        """Get memory window state and conversation summary"""
        doc = self.chat_history.find_one({"session_id": session_id, "video_id": video_id})
        if doc and "memory_state" in doc:
            return doc["memory_state"]
        return {
            "conversation_summary": "",
            "total_messages_processed": 0,
            "active_window_start_index": 0,
            "last_summarization_index": 0,
            "last_summarized_at": datetime.utcnow()
        }

    def mark_messages_as_original(self, session_id: str, start_index: int, end_index: int):
        """Mark messages in range as original (not summarized)"""
        doc = self.chat_history.find_one({"session_id": session_id})
        if doc and "messages" in doc:
            for i in range(start_index, min(end_index, len(doc["messages"]))):
                if i >= 0:
                    self.chat_history.update_one(
                        {"session_id": session_id},
                        {
                            "$set": {
                                f"messages.{i}.is_original": True,
                                f"messages.{i}.summarized_from_indices": []
                            }
                        }
                    )

    def mark_message_as_summary(self, session_id: str, new_message: str, summarized_from_indices: list):
        """Add a summary message and mark it as non-original"""
        msg = MessageModel(role="system", message=new_message).dict()
        msg["is_original"] = False  # Mark as summarized
        msg["summarized_from_indices"] = summarized_from_indices
        
        self.chat_history.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": msg},
                "$set": {"last_updated": datetime.utcnow()}
            }
        )

    def get_original_messages(self, session_id: str, from_index: int = 0) -> List[dict]:
        """Get only original messages (not summaries) from specified index"""
        doc = self.chat_history.find_one({"session_id": session_id})
        if not doc or "messages" not in doc:
            return []
        
        messages = doc["messages"]
        original_messages = [
            (i, msg) for i, msg in enumerate(messages[from_index:], start=from_index)
            if msg.get("is_original", True)  # Default to True for backward compatibility
        ]
        return original_messages

    def delete_messages_by_index(self, session_id: str, indices_to_delete: list):
        """Delete messages by their indices (used after summarization)"""
        doc = self.chat_history.find_one({"session_id": session_id})
        if doc and "messages" in doc:
            # Keep messages NOT in the deletion list
            messages = doc["messages"]
            messages_to_keep = [msg for i, msg in enumerate(messages) if i not in indices_to_delete]
            self.chat_history.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "messages": messages_to_keep,
                        "last_updated": datetime.utcnow()
                    }
                }
            )
    
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
    
    def disconnect(self):
        """Gracefully disconnect from MongoDB connection pool."""
        _mongo_singleton.disconnect()
        

