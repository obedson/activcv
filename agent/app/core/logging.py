"""
Comprehensive logging configuration for the application
"""

import logging
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry)


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_FIELDS = [
        'password', 'token', 'api_key', 'secret', 'authorization',
        'cookie', 'session', 'csrf', 'private_key', 'credit_card'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitize the message
        message = record.getMessage().lower()
        
        # Check if message contains sensitive information
        for field in self.SENSITIVE_FIELDS:
            if field in message:
                # Replace sensitive data with [REDACTED]
                record.msg = self._sanitize_message(record.msg)
                break
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize sensitive information from log messages"""
        import re
        
        # Common patterns for sensitive data
        patterns = [
            (r'(password["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', r'\1[REDACTED]'),
            (r'(token["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', r'\1[REDACTED]'),
            (r'(api_key["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', r'\1[REDACTED]'),
            (r'(authorization["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', r'\1[REDACTED]'),
            (r'(Bearer\s+)([A-Za-z0-9\-_]+)', r'\1[REDACTED]'),
            (r'(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})', r'[CREDIT_CARD_REDACTED]'),
        ]
        
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized


def setup_logging():
    """Setup comprehensive application logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output for development
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT == "development":
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SecurityFilter())
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logging
    file_handler = logging.FileHandler(settings.LOG_FILE)
    file_formatter = JSONFormatter()
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(SecurityFilter())
    root_logger.addHandler(file_handler)
    
    # Error file handler for errors only
    error_handler = logging.FileHandler('logs/errors.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    error_handler.addFilter(SecurityFilter())
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Application logger
    logger = logging.getLogger("ai_cv_agent")
    logger.info("Logging configured successfully", extra={
        "log_level": settings.LOG_LEVEL,
        "environment": settings.ENVIRONMENT
    })


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(f"ai_cv_agent.{name}")


class LoggerMixin:
    """Mixin to add logging capabilities to classes"""
    
    @property
    def logger(self) -> logging.Logger:
        return get_logger(self.__class__.__name__)
    
    def log_operation(self, operation: str, **kwargs):
        """Log an operation with additional context"""
        self.logger.info(f"Operation: {operation}", extra={
            "operation": operation,
            **kwargs
        })
    
    def log_error(self, error: Exception, operation: str = None, **kwargs):
        """Log an error with context"""
        self.logger.error(
            f"Error in {operation or 'unknown operation'}: {str(error)}",
            exc_info=True,
            extra={
                "operation": operation,
                "error_type": type(error).__name__,
                **kwargs
            }
        )
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        self.logger.info(
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            extra={
                "operation": operation,
                "duration_ms": duration_ms,
                "performance_log": True,
                **kwargs
            }
        )


def log_api_call(func):
    """Decorator to log API calls"""
    import functools
    import time
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger("api")
        start_time = time.time()
        
        # Extract request info if available
        request_info = {}
        for arg in args:
            if hasattr(arg, 'method') and hasattr(arg, 'url'):
                request_info = {
                    "method": arg.method,
                    "path": str(arg.url.path),
                    "query_params": dict(arg.query_params)
                }
                break
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"API call completed: {func.__name__}",
                extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "success": True,
                    **request_info
                }
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                f"API call failed: {func.__name__} - {str(e)}",
                exc_info=True,
                extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "success": False,
                    "error_type": type(e).__name__,
                    **request_info
                }
            )
            
            raise
    
    return wrapper


# Create application logger instance
logger = get_logger("main")