"""
IMMEDIATE FIX: Update FastAPI validators to accept MongoDB ObjectId format

File: chatbot/models/validators.py

This fix allows FastAPI to accept both:
1. MongoDB ObjectId format (24 hex characters): "507f1f77bcf86cd799439011"
2. UUID format (standard): "550e8400-e29b-41d4-a716-446655440000"

This resolves the 422 error when Express sends ObjectId strings to FastAPI.
"""

import re
import uuid
from typing import Optional
from pydantic import field_validator, Field


# ISO 639-1 language codes whitelist
VALID_LANGUAGE_CODES = {
    'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'ru', 'ja', 'zh',
    'ko', 'ar', 'hi', 'th', 'tr', 'pl', 'uk', 'vi', 'id', 'he',
    'fa', 'ur', 'bn', 'pa', 'ta', 'te', 'kn', 'ml', 'my', 'khmer',
    'lao', 'gu', 'mr', 'as'
}

YOUTUBE_VIDEO_ID_PATTERN = r'^[a-zA-Z0-9_-]{11}$'
MONGODB_OBJECTID_PATTERN = r'^[a-f0-9]{24}$'  # MongoDB ObjectId is 24 hex chars


def validate_video_id(value: str) -> str:
    """Validate YouTube video ID format.
    
    Args:
        value: Video ID to validate (should be 11 chars, alphanumeric, underscore, hyphen)
        
    Returns:
        The validated video ID
        
    Raises:
        ValueError: If video ID format is invalid
    """
    if not value:
        raise ValueError("video_id cannot be empty")
    
    if len(value) > 100:  # Safety check for length
        raise ValueError("video_id exceeds maximum length of 100 characters")
    
    if not re.match(YOUTUBE_VIDEO_ID_PATTERN, value):
        raise ValueError(
            "video_id must be 11 characters long and contain only alphanumeric characters, hyphens, and underscores"
        )
    return value


def validate_query(value: str) -> str:
    """Validate query string.
    
    Args:
        value: Query string to validate
        
    Returns:
        The validated query
        
    Raises:
        ValueError: If query fails validation
    """
    if not value:
        raise ValueError("query cannot be empty")
    
    if len(value) < 1:
        raise ValueError("query must be at least 1 character long")
    
    if len(value) > 5000:
        raise ValueError("query exceeds maximum length of 5000 characters")
    
    # Basic check for potential injection patterns (not comprehensive, for defense in depth)
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',  # onload=, onclick=, etc.
    ]
    
    query_lower = value.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, query_lower):
            raise ValueError("query contains potentially malicious content")
    
    return value


def validate_user_id(value: Optional[str]) -> Optional[str]:
    """Validate user ID format - accepts BOTH MongoDB ObjectId and UUID formats.
    
    This is crucial for Express→FastAPI integration where user_id comes from MongoDB ObjectId.
    
    Args:
        value: User ID to validate
               - MongoDB ObjectId: 24 character hex string (e.g., "507f1f77bcf86cd799439011")
               - UUID: standard format (e.g., "550e8400-e29b-41d4-a716-446655440000")
        
    Returns:
        The validated user ID or None
        
    Raises:
        ValueError: If user ID is not a valid ObjectId or UUID
    """
    if value is None:
        return None
    
    if not value:
        raise ValueError("user_id cannot be empty string (use None instead)")
    
    # Check if it's a valid MongoDB ObjectId (24 hex characters)
    if re.match(MONGODB_OBJECTID_PATTERN, value.lower()):
        return value
    
    # Try to parse as UUID
    try:
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        pass
    
    # Neither format matched
    raise ValueError(
        f"user_id must be either a valid MongoDB ObjectId (24 hex characters) "
        f"or a standard UUID (e.g., 550e8400-e29b-41d4-a716-446655440000) "
        f"(got: {value})"
    )


def validate_session_id(value: Optional[str]) -> Optional[str]:
    """Validate session ID format (UUID).
    
    Args:
        value: Session ID to validate (should be valid UUID or None)
        
    Returns:
        The validated session ID or None
        
    Raises:
        ValueError: If session ID is not a valid UUID
    """
    if value is None:
        return None
    
    if not value:
        raise ValueError("session_id cannot be empty string (use None instead)")
    
    try:
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        raise ValueError(
            f"session_id must be a valid UUID (e.g., 550e8400-e29b-41d4-a716-446655440000) "
            f"(got: {value})"
        )


def validate_language_code(value: Optional[str]) -> Optional[str]:
    """Validate language code (ISO 639-1).
    
    Args:
        value: Language code to validate
        
    Returns:
        The validated language code or None
        
    Raises:
        ValueError: If language code is invalid
    """
    if value is None:
        return None
    
    if not value:
        raise ValueError("language_code cannot be empty string (use None instead)")
    
    if len(value) > 5:
        raise ValueError("language_code exceeds maximum length of 5 characters")
    
    if value.lower() not in VALID_LANGUAGE_CODES:
        raise ValueError(
            f"language_code '{value}' is not a valid ISO 639-1 code. "
            f"Valid codes: {', '.join(sorted(VALID_LANGUAGE_CODES[:10]))}... (see {len(VALID_LANGUAGE_CODES)} total)"
        )
    
    return value
