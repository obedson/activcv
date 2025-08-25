"""
Custom exception classes for the AI CV Agent application
"""

from typing import Any, Dict, Optional


class AIAgentException(Exception):
    """Base exception class for AI CV Agent"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AIAgentException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": value}
        )


class AuthenticationError(AIAgentException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(AIAgentException):
    """Raised when user lacks permission for an action"""
    
    def __init__(self, message: str = "Access denied", resource: str = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details={"resource": resource}
        )


class ResourceNotFoundError(AIAgentException):
    """Raised when a requested resource is not found"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class FileProcessingError(AIAgentException):
    """Raised when file processing fails"""
    
    def __init__(self, message: str, file_name: str = None, file_type: str = None):
        super().__init__(
            message=message,
            error_code="FILE_PROCESSING_ERROR",
            details={"file_name": file_name, "file_type": file_type}
        )


class AIServiceError(AIAgentException):
    """Raised when AI service operations fail"""
    
    def __init__(self, message: str, service: str = None, operation: str = None):
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            details={"service": service, "operation": operation}
        )


class DatabaseError(AIAgentException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None, table: str = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation, "table": table}
        )


class StorageError(AIAgentException):
    """Raised when storage operations fail"""
    
    def __init__(self, message: str, operation: str = None, file_path: str = None):
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            details={"operation": operation, "file_path": file_path}
        )


class RateLimitError(AIAgentException):
    """Raised when rate limits are exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", limit: int = None, window: str = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details={"limit": limit, "window": window}
        )


class ExternalServiceError(AIAgentException):
    """Raised when external service calls fail"""
    
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "status_code": status_code}
        )


class ConfigurationError(AIAgentException):
    """Raised when configuration is invalid or missing"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key}
        )


class JobProcessingError(AIAgentException):
    """Raised when background job processing fails"""
    
    def __init__(self, message: str, job_type: str = None, job_id: str = None):
        super().__init__(
            message=message,
            error_code="JOB_PROCESSING_ERROR",
            details={"job_type": job_type, "job_id": job_id}
        )


class TemplateError(AIAgentException):
    """Raised when template processing fails"""
    
    def __init__(self, message: str, template_name: str = None, template_type: str = None):
        super().__init__(
            message=message,
            error_code="TEMPLATE_ERROR",
            details={"template_name": template_name, "template_type": template_type}
        )


class PDFGenerationError(AIAgentException):
    """Raised when PDF generation fails"""
    
    def __init__(self, message: str, template: str = None, content_length: int = None):
        super().__init__(
            message=message,
            error_code="PDF_GENERATION_ERROR",
            details={"template": template, "content_length": content_length}
        )


class EmailServiceError(AIAgentException):
    """Raised when email service operations fail"""
    
    def __init__(self, message: str, recipient: str = None, email_type: str = None):
        super().__init__(
            message=message,
            error_code="EMAIL_SERVICE_ERROR",
            details={"recipient": recipient, "email_type": email_type}
        )


class CrawlingError(AIAgentException):
    """Raised when web crawling operations fail"""
    
    def __init__(self, message: str, url: str = None, site_name: str = None):
        super().__init__(
            message=message,
            error_code="CRAWLING_ERROR",
            details={"url": url, "site_name": site_name}
        )


class MatchingError(AIAgentException):
    """Raised when job matching operations fail"""
    
    def __init__(self, message: str, user_id: str = None, job_count: int = None):
        super().__init__(
            message=message,
            error_code="MATCHING_ERROR",
            details={"user_id": user_id, "job_count": job_count}
        )