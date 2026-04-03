"""Input validators for request models using Pydantic field validators."""
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
    """Validate user ID format (UUID).
    
    Args:
        value: User ID to validate (should be valid UUID or None)
        
    Returns:
        The validated user ID or None
        
    Raises:
        ValueError: If user ID is not a valid UUID
    """
    if value is None:
        return None
    
    if not value:
        raise ValueError("user_id cannot be empty string (use None instead)")
    
    try:
        # Validate UUID format
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        raise ValueError(
            f"user_id must be a valid UUID (got: {value})"
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
    
    if len(value) > 10:
        raise ValueError("language_code exceeds maximum length of 10 characters")
    
    value_lower = value.lower()
    if value_lower not in VALID_LANGUAGE_CODES:
        raise ValueError(
            f"language_code '{value}' is not a valid ISO 639-1 language code. "
            f"Valid codes include: en, es, fr, de, it, pt, ja, zh, ko, etc."
        )
    
    return value_lower


def validate_session_id(value: str) -> str:
    """Validate session ID format (UUID).
    
    Args:
        value: Session ID to validate
        
    Returns:
        The validated session ID
        
    Raises:
        ValueError: If session ID is not a valid UUID
    """
    if not value:
        raise ValueError("session_id cannot be empty")
    
    try:
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        raise ValueError(
            f"session_id must be a valid UUID (got: {value})"
        )
