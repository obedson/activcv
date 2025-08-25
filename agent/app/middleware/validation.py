"""
Input validation and sanitization middleware
"""

import re
import html
from typing import Any, Dict, List
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import ValidationError


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization"""
    
    def __init__(self, app, max_request_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_request_size = max_request_size
        
        # Dangerous patterns to block
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframes
            r'<object[^>]*>.*?</object>',  # Objects
            r'<embed[^>]*>.*?</embed>',  # Embeds
            r'<link[^>]*>',  # Link tags
            r'<meta[^>]*>',  # Meta tags
            r'<style[^>]*>.*?</style>',  # Style tags
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
            r'(\b(OR|AND)\s+[\'"]?\w+[\'"]?\s*=\s*[\'"]?\w+[\'"]?)',
            r'(--|#|/\*|\*/)',
            r'(\bxp_\w+)',
            r'(\bsp_\w+)',
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through validation middleware"""
        
        # Check request size
        if hasattr(request, 'headers') and 'content-length' in request.headers:
            content_length = int(request.headers['content-length'])
            if content_length > self.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large. Maximum size: {self.max_request_size} bytes"
                )
        
        # Validate and sanitize request data
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Get request body for validation
                body = await request.body()
                if body:
                    # For JSON requests, validate the content
                    if request.headers.get('content-type', '').startswith('application/json'):
                        import json
                        try:
                            data = json.loads(body)
                            self._validate_json_data(data)
                        except json.JSONDecodeError:
                            raise ValidationError("Invalid JSON format")
                        except Exception as e:
                            raise ValidationError(f"JSON validation failed: {str(e)}")
                
                # Recreate request with validated body
                request._body = body
                
            except ValidationError:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Request validation failed: {str(e)}")
        
        # Validate query parameters
        if request.query_params:
            self._validate_query_params(dict(request.query_params))
        
        # Validate path parameters
        if hasattr(request, 'path_params') and request.path_params:
            self._validate_path_params(request.path_params)
        
        response = await call_next(request)
        return response
    
    def _validate_json_data(self, data: Any, path: str = "root") -> None:
        """Recursively validate JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                # Validate key
                self._validate_string(key, f"{path}.{key}")
                # Validate value
                self._validate_json_data(value, f"{path}.{key}")
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_json_data(item, f"{path}[{i}]")
                
        elif isinstance(data, str):
            self._validate_string(data, path)
    
    def _validate_string(self, value: str, field_name: str = "field") -> str:
        """Validate and sanitize string input"""
        if not isinstance(value, str):
            return value
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                raise ValidationError(
                    f"Potentially dangerous content detected in {field_name}",
                    field=field_name,
                    value=value[:100] + "..." if len(value) > 100 else value
                )
        
        # Check for SQL injection patterns
        for pattern in self.sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    f"Potential SQL injection detected in {field_name}",
                    field=field_name,
                    value=value[:100] + "..." if len(value) > 100 else value
                )
        
        # Basic length validation
        if len(value) > 10000:  # 10KB limit for individual strings
            raise ValidationError(
                f"String too long in {field_name}. Maximum length: 10000 characters",
                field=field_name
            )
        
        return value
    
    def _validate_query_params(self, params: Dict[str, str]) -> None:
        """Validate query parameters"""
        for key, value in params.items():
            self._validate_string(key, f"query_param.{key}")
            self._validate_string(value, f"query_param.{key}")
    
    def _validate_path_params(self, params: Dict[str, str]) -> None:
        """Validate path parameters"""
        for key, value in params.items():
            # Path params should be more restrictive
            if not re.match(r'^[a-zA-Z0-9_-]+$', str(value)):
                raise ValidationError(
                    f"Invalid characters in path parameter {key}",
                    field=f"path_param.{key}",
                    value=value
                )
            
            if len(str(value)) > 100:
                raise ValidationError(
                    f"Path parameter {key} too long",
                    field=f"path_param.{key}"
                )


class RequestSanitizerMiddleware(BaseHTTPMiddleware):
    """Middleware for sanitizing request data"""
    
    async def dispatch(self, request: Request, call_next):
        """Sanitize request data"""
        
        # Add request ID for tracking
        import uuid
        request.state.request_id = str(uuid.uuid4())
        
        # Add security headers to response
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request.state.request_id
        
        return response


def sanitize_html(text: str) -> str:
    """Sanitize HTML content"""
    if not text:
        return text
    
    # Escape HTML entities
    sanitized = html.escape(text)
    
    # Remove any remaining script tags or dangerous content
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'meta', 'style']
    for tag in dangerous_tags:
        pattern = f'<{tag}[^>]*>.*?</{tag}>'
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Also remove self-closing tags
        pattern = f'<{tag}[^>]*/?>'
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    return sanitized


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    return 7 <= len(digits) <= 15


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))


def validate_file_name(filename: str) -> bool:
    """Validate file name"""
    # Check for dangerous characters
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    
    for char in dangerous_chars:
        if char in filename:
            return False
    
    # Check length
    if len(filename) > 255:
        return False
    
    # Check for valid extension
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png']
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        return False
    
    return True


class FileValidationMixin:
    """Mixin for file validation utilities"""
    
    @staticmethod
    def validate_file_size(file_size: int, max_size: int = 50 * 1024 * 1024) -> bool:
        """Validate file size"""
        return 0 < file_size <= max_size
    
    @staticmethod
    def validate_file_type(content_type: str, allowed_types: List[str]) -> bool:
        """Validate file content type"""
        return content_type in allowed_types
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return filename.lower().split('.')[-1] if '.' in filename else ''