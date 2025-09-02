"""
Security middleware for FastAPI application
"""

import time
import logging
import hashlib
import re
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import redis
from ipaddress import ip_address, ip_network

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.rate_limits = self._load_rate_limits()
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns = self._load_suspicious_patterns()
        self.trusted_networks = self._load_trusted_networks()
    
    def _load_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Load rate limiting configuration"""
        return {
            "default": {"requests": 60, "window": 60},  # 60 requests per minute
            "auth": {"requests": 5, "window": 300},     # 5 auth attempts per 5 minutes
            "upload": {"requests": 10, "window": 3600}, # 10 uploads per hour
            "generation": {"requests": 20, "window": 3600}, # 20 generations per hour
        }
    
    def _load_suspicious_patterns(self) -> list:
        """Load patterns that indicate suspicious activity"""
        return [
            r"(?i)(union|select|insert|delete|drop|create|alter|exec|script)",  # SQL injection
            r"(?i)(<script|javascript:|vbscript:|onload=|onerror=)",           # XSS
            r"(?i)(\.\.\/|\.\.\\|\/etc\/|\/proc\/|\/sys\/)",                   # Path traversal
            r"(?i)(cmd|powershell|bash|sh|exec|system|eval)",                  # Command injection
            r"(?i)(base64|hex|url|html)encode",                                # Encoding attacks
        ]
    
    def _load_trusted_networks(self) -> list:
        """Load trusted IP networks"""
        return [
            ip_network("127.0.0.0/8"),    # Localhost
            ip_network("10.0.0.0/8"),     # Private network
            ip_network("172.16.0.0/12"),  # Private network
            ip_network("192.168.0.0/16"), # Private network
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Main security middleware dispatch"""
        start_time = time.time()
        
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Security checks
            await self._check_ip_blocking(client_ip)
            await self._check_rate_limiting(request, client_ip)
            await self._check_request_validation(request)
            await self._check_suspicious_activity(request, client_ip)
            
            # Add security headers to request
            self._add_security_context(request, client_ip)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            # Log successful request
            processing_time = time.time() - start_time
            await self._log_request(request, response, client_ip, processing_time)
            
            return response
            
        except HTTPException as e:
            # Log security violation
            processing_time = time.time() - start_time
            await self._log_security_violation(request, client_ip, str(e.detail), processing_time)
            
            # Return security error response
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "timestamp": datetime.utcnow().isoformat()}
            )
            
        except Exception as e:
            # Log unexpected error
            logger.error(f"Security middleware error: {e}")
            processing_time = time.time() - start_time
            await self._log_security_violation(request, client_ip, f"Middleware error: {str(e)}", processing_time)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal security error", "timestamp": datetime.utcnow().isoformat()}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _check_ip_blocking(self, client_ip: str):
        """Check if IP is blocked"""
        if client_ip in self.blocked_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address is blocked"
            )
        
        # Check Redis for blocked IPs
        if self.redis_client:
            try:
                is_blocked = await self.redis_client.get(f"blocked_ip:{client_ip}")
                if is_blocked:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="IP address is temporarily blocked"
                    )
            except Exception as e:
                logger.warning(f"Redis IP check failed: {e}")
    
    async def _check_rate_limiting(self, request: Request, client_ip: str):
        """Check rate limiting"""
        if not self.redis_client:
            return
        
        # Determine rate limit category
        path = request.url.path
        category = self._get_rate_limit_category(path)
        
        rate_config = self.rate_limits.get(category, self.rate_limits["default"])
        
        # Create rate limit key
        window_start = int(time.time()) // rate_config["window"]
        rate_key = f"rate_limit:{client_ip}:{category}:{window_start}"
        
        try:
            # Get current request count
            current_requests = await self.redis_client.get(rate_key)
            current_requests = int(current_requests) if current_requests else 0
            
            # Check if limit exceeded
            if current_requests >= rate_config["requests"]:
                # Block IP temporarily for repeated violations
                await self._handle_rate_limit_violation(client_ip, category)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {category}. Try again later."
                )
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, rate_config["window"])
            await pipe.execute()
            
        except redis.RedisError as e:
            logger.warning(f"Redis rate limiting failed: {e}")
            # Continue without rate limiting if Redis is unavailable
    
    def _get_rate_limit_category(self, path: str) -> str:
        """Determine rate limit category based on path"""
        if "/auth/" in path or "/login" in path or "/register" in path:
            return "auth"
        elif "/upload" in path:
            return "upload"
        elif "/generate" in path or "/job-processing" in path:
            return "generation"
        else:
            return "default"
    
    async def _handle_rate_limit_violation(self, client_ip: str, category: str):
        """Handle rate limit violations"""
        if not self.redis_client:
            return
        
        try:
            # Track violations
            violation_key = f"rate_violations:{client_ip}"
            violations = await self.redis_client.incr(violation_key)
            await self.redis_client.expire(violation_key, 3600)  # 1 hour window
            
            # Block IP after multiple violations
            if violations >= 5:
                block_key = f"blocked_ip:{client_ip}"
                await self.redis_client.setex(block_key, 1800, "rate_limit_violations")  # 30 min block
                logger.warning(f"IP {client_ip} blocked for rate limit violations")
                
        except redis.RedisError as e:
            logger.warning(f"Failed to handle rate limit violation: {e}")
    
    async def _check_request_validation(self, request: Request):
        """Validate request structure and size"""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            max_size = getattr(settings, 'MAX_REQUEST_SIZE_MB', 50)
            
            if size_mb > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request too large. Maximum size: {max_size}MB"
                )
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Allow common content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            
            if not any(allowed_type in content_type for allowed_type in allowed_types):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported content type"
                )
    
    async def _check_suspicious_activity(self, request: Request, client_ip: str):
        """Check for suspicious activity patterns"""
        # Check URL for suspicious patterns
        full_url = str(request.url)
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, full_url):
                await self._log_suspicious_activity(client_ip, "suspicious_url", full_url)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request format"
                )
        
        # Check headers for suspicious content
        for header_name, header_value in request.headers.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, header_value):
                    await self._log_suspicious_activity(client_ip, "suspicious_header", f"{header_name}: {header_value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request headers"
                    )
        
        # Check user agent
        user_agent = request.headers.get("user-agent", "")
        if self._is_suspicious_user_agent(user_agent):
            await self._log_suspicious_activity(client_ip, "suspicious_user_agent", user_agent)
            # Don't block, just log for now
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        suspicious_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp",
            "wget", "curl", "python-requests", "bot", "crawler",
            "scanner", "exploit"
        ]
        
        user_agent_lower = user_agent.lower()
        return any(agent in user_agent_lower for agent in suspicious_agents)
    
    def _add_security_context(self, request: Request, client_ip: str):
        """Add security context to request"""
        request.state.client_ip = client_ip
        request.state.is_trusted = self._is_trusted_ip(client_ip)
        request.state.request_id = self._generate_request_id(request)
    
    def _is_trusted_ip(self, client_ip: str) -> bool:
        """Check if IP is in trusted networks"""
        try:
            ip = ip_address(client_ip)
            return any(ip in network for network in self.trusted_networks)
        except ValueError:
            return False
    
    def _generate_request_id(self, request: Request) -> str:
        """Generate unique request ID"""
        timestamp = str(int(time.time() * 1000))
        path_hash = hashlib.md5(request.url.path.encode()).hexdigest()[:8]
        return f"{timestamp}-{path_hash}"
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
    
    async def _log_request(self, request: Request, response: Response, client_ip: str, processing_time: float):
        """Log successful request"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", "unknown"),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time_ms": round(processing_time * 1000, 2),
            "user_agent": request.headers.get("user-agent", ""),
            "is_trusted": getattr(request.state, "is_trusted", False)
        }
        
        # Log to structured logger
        logger.info("Request processed", extra=log_data)
    
    async def _log_security_violation(self, request: Request, client_ip: str, violation: str, processing_time: float):
        """Log security violation"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", "unknown"),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "violation": violation,
            "processing_time_ms": round(processing_time * 1000, 2),
            "user_agent": request.headers.get("user-agent", ""),
            "headers": dict(request.headers)
        }
        
        logger.warning("Security violation detected", extra=log_data)
        
        # Store in Redis for analysis
        if self.redis_client:
            try:
                violation_key = f"security_violations:{client_ip}"
                await self.redis_client.lpush(violation_key, str(log_data))
                await self.redis_client.expire(violation_key, 86400)  # Keep for 24 hours
            except redis.RedisError as e:
                logger.error(f"Failed to store security violation: {e}")
    
    async def _log_suspicious_activity(self, client_ip: str, activity_type: str, details: str):
        """Log suspicious activity"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "activity_type": activity_type,
            "details": details
        }
        
        logger.warning("Suspicious activity detected", extra=log_data)
        
        # Store in Redis for analysis
        if self.redis_client:
            try:
                activity_key = f"suspicious_activity:{client_ip}"
                await self.redis_client.lpush(activity_key, str(log_data))
                await self.redis_client.expire(activity_key, 86400)  # Keep for 24 hours
            except redis.RedisError as e:
                logger.error(f"Failed to store suspicious activity: {e}")


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = {"/api/v1/health", "/docs", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """CSRF protection dispatch"""
        # Skip CSRF for safe methods and exempt paths
        if request.method in ["GET", "HEAD", "OPTIONS"] or request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Check CSRF token for state-changing requests
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "CSRF token required"}
            )
        
        # Validate CSRF token (implement your validation logic)
        if not self._validate_csrf_token(csrf_token, request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Invalid CSRF token"}
            )
        
        return await call_next(request)
    
    def _validate_csrf_token(self, token: str, request: Request) -> bool:
        """Validate CSRF token"""
        # Implement your CSRF token validation logic here
        # This is a simplified example
        expected_token = self._generate_csrf_token(request)
        return token == expected_token
    
    def _generate_csrf_token(self, request: Request) -> str:
        """Generate CSRF token"""
        # Implement your CSRF token generation logic here
        # This is a simplified example
        session_id = request.headers.get("Authorization", "")
        return hashlib.sha256(f"{session_id}:{settings.JWT_SECRET_KEY}".encode()).hexdigest()[:32]


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Input sanitization middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.dangerous_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Input sanitization dispatch"""
        # Only process requests with body
        if request.method in ["POST", "PUT", "PATCH"]:
            # Note: This is a basic example. In production, you'd want more sophisticated
            # sanitization that preserves legitimate content while removing threats
            pass
        
        return await call_next(request)


# Utility functions for security middleware

def get_security_middleware(redis_client: Optional[redis.Redis] = None) -> SecurityMiddleware:
    """Factory function to create security middleware"""
    return SecurityMiddleware(None, redis_client)


def get_csrf_middleware() -> CSRFMiddleware:
    """Factory function to create CSRF middleware"""
    return CSRFMiddleware(None)


def get_input_sanitization_middleware() -> InputSanitizationMiddleware:
    """Factory function to create input sanitization middleware"""
    return InputSanitizationMiddleware(None)