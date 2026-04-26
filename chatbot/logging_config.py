import logging
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional
import inspect

class StructuredFormatter(logging.Formatter):
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present (SANITIZED to remove API keys)
        if record.exc_info:
            exc_message = str(record.exc_info[1])
            sanitized_message = sanitize_exception_message(exc_message)
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": sanitized_message,
                "traceback": self.formatException(record.exc_info),
            }
        
        # Add custom fields if attached to the record
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, default=str)


class AuditLogger:
    """Audit logging for security events."""
    
    def __init__(self, name: str = "audit"):
        self.logger = logging.getLogger(f"{name}.audit")
        self.logger.setLevel(logging.INFO)
    
    def log_auth_attempt(
        self,
        email: str,
        action: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log authentication attempt.
        
        Args:
            email: User email
            action: Auth action (login/register/logout)
            success: Whether action succeeded
            ip_address: Client IP address
            user_agent: Client user agent
            error: Error message if unsuccessful
        """
        audit_data = {
            "event_type": "auth_attempt",
            "action": action,
            "email": email,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if error:
            audit_data["error"] = error
        
        log_record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            "(audit)",
            0,
            f"Auth {action}: {email} - {'success' if success else 'failed'}",
            (),
            None,
        )
        log_record.extra_data = audit_data
        self.logger.handle(log_record)
    
    def log_resource_access(
        self,
        user_id: str,
        resource: str,  # endpoint/resource accessed
        action: str,  # "read", "write", "delete"
        success: bool,
        ip_address: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log resource access (Issue 34).
        
        Args:
            user_id: User identifier
            resource: Resource or endpoint accessed
            action: Action performed (read/write/delete)
            success: Whether action succeeded
            ip_address: Client IP address
            error: Error message if unsuccessful
        """
        audit_data = {
            "event_type": "resource_access",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if error:
            audit_data["error"] = error
        
        log_record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            "(audit)",
            0,
            f"Access {resource}: {action} - {'success' if success else 'failed'}",
            (),
            None,
        )
        log_record.extra_data = audit_data
        self.logger.handle(log_record)
    
    def log_security_event(
        self,
        event_type: str,  # "failed_login_attempts", "suspicious_activity", etc.
        severity: str,  # "low", "medium", "high", "critical"
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        description: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security event (Issue 34).
        
        Args:
            event_type: Type of security event
            severity: Severity level
            user_id: User identifier if applicable
            ip_address: Client IP address
            description: Event description
            additional_data: Additional context data
        """
        audit_data = {
            "event_type": "security_event",
            "security_event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if additional_data:
            audit_data.update(additional_data)
        
        level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }.get(severity, logging.INFO)
        
        log_record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(audit)",
            0,
            f"Security event [{severity}]: {event_type}",
            (),
            None,
        )
        log_record.extra_data = audit_data
        self.logger.handle(log_record)


def setup_structured_logging(app_name: str = "yt-chatbot") -> logging.Logger:
    """Configure structured logging for the application (Issue 40).
    
    Sets up JSON-formatted logging with configurable log levels.
    
    Args:
        app_name: Application name for logger identification
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment (default: INFO)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Get log format preference (json or text)
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    if log_format == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        # Text format as fallback
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Optional: File handler for audit logs
    audit_log_path = os.getenv("AUDIT_LOG_FILE")
    if audit_log_path:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
            
            file_handler = logging.FileHandler(audit_log_path)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to setup audit log file: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger with structured configuration (Issue 40).
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Ensure handler exists
    if not logger.handlers:
        parent_logger = logging.getLogger("yt-chatbot")
        if parent_logger.handlers:
            logger.handlers = parent_logger.handlers
            logger.setLevel(parent_logger.level)
        else:
            # Setup default if no parent configured
            setup_structured_logging()
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context_data,
) -> None:
    """Log message with context data (Issue 40).
    
    Attaches context data to log record for structured output.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **context_data: Additional context to include in structured log
    """
    record = logger.makeRecord(
        logger.name,
        level,
        "",  # pathname
        0,   # lineno
        message,
        (),  # args
        None,  # exc_info
    )
    
    record.extra_data = context_data
    logger.handle(record)


# Global audit logger instance
audit_logger = AuditLogger()


def sanitize_exception_message(message: str) -> str:
    """Sanitize exception messages to remove sensitive data (API keys, URLs with credentials).
    
    Args:
        message: Raw exception message that may contain sensitive data
        
    Returns:
        Sanitized message with API keys and credentials masked
    """
    if not message:
        return message
    
    # Mask common API key patterns
    patterns = [
        (r'key=[^&\s"\']+', 'key=***'),  # key=xxx
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+', 'api_key=***'),  # api_key=xxx
        (r'authorization["\']?\s*[:=]\s*["\']?Bearer\s+[a-zA-Z0-9_.-]+', 'authorization=Bearer ***'),  # Bearer token
        (r'google[_-]?api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+', 'google_api_key=***'),  # Google API key
        (r'AQ\.[a-zA-Z0-9_-]{50,}', 'AQ.***'),  # Google OAuth token format
        (r'AIza[a-zA-Z0-9_-]{35}', 'AIza***'),  # Google API key format
        (r'(?:mongodb|postgres|mysql)://[^@]+@', r'://***@'),  # Database connection strings
    ]
    
    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized
