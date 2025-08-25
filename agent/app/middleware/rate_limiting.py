"""
Rate limiting middleware for API endpoints
"""

import time
import json
from typing import Dict, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rate_limiting")


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development"""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict]:
        """Check if request is allowed under rate limit"""
        now = time.time()
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < window]
        else:
            self.requests[key] = []
        
        # Check if under limit
        current_count = len(self.requests[key])
        
        if current_count >= limit:
            # Calculate reset time
            oldest_request = min(self.requests[key]) if self.requests[key] else now
            reset_time = oldest_request + window
            
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": int(reset_time),
                "retry_after": int(reset_time - now)
            }
        
        # Add current request
        self.requests[key].append(now)
        
        return True, {
            "limit": limit,
            "remaining": limit - current_count - 1,
            "reset": int(now + window),
            "retry_after": 0
        }


class RedisRateLimiter:
    """Redis-based rate limiter for production"""
    
    def __init__(self, redis_url: str):
        try:
            import redis
            self.redis = redis.from_url(redis_url)
        except ImportError:
            logger.warning("Redis not available, falling back to in-memory rate limiter")
            self.redis = None
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict]:
        """Check if request is allowed under rate limit"""
        if not self.redis:
            # Fallback to in-memory limiter
            return InMemoryRateLimiter().is_allowed(key, limit, window)
        
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            
            # Use sliding window log algorithm
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= limit:
                # Get oldest request for reset calculation
                oldest = self.redis.zrange(key, 0, 0, withscores=True)
                reset_time = oldest[0][1] + window if oldest else now + window
                
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": int(reset_time),
                    "retry_after": int(reset_time - now)
                }
            
            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset": int(now + window),
                "retry_after": 0
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            # Fallback to allowing the request
            return True, {"limit": limit, "remaining": limit - 1, "reset": int(time.time() + window), "retry_after": 0}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, rate_limiter: Optional[object] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or self._get_default_limiter()
        
        # Rate limit configurations for different endpoints
        self.endpoint_limits = {
            "/api/v1/uploads": {"limit": 10, "window": 3600},  # 10 uploads per hour
            "/api/v1/jobs/generate-cv": {"limit": 5, "window": 3600},  # 5 CV generations per hour
            "/api/v1/cover-letters/generate": {"limit": 10, "window": 3600},  # 10 cover letters per hour
            "/api/v1/jobs/crawl": {"limit": 3, "window": 3600},  # 3 manual crawls per hour
            "default": {"limit": settings.RATE_LIMIT_PER_MINUTE, "window": 60}  # Default rate limit
        }
    
    def _get_default_limiter(self):
        """Get default rate limiter based on configuration"""
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            return RedisRateLimiter(settings.REDIS_URL)
        else:
            return InMemoryRateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests"""
        
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get rate limit configuration for this endpoint
        limit_config = self._get_limit_config(request.url.path, request.method)
        
        # Create rate limit key
        rate_limit_key = f"rate_limit:{client_id}:{request.url.path}:{request.method}"
        
        # Check rate limit
        allowed, info = self.rate_limiter.is_allowed(
            rate_limit_key,
            limit_config["limit"],
            limit_config["window"]
        )
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id}",
                extra={
                    "client_id": client_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "limit": info["limit"],
                    "retry_after": info["retry_after"]
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": info["retry_after"]
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["retry_after"])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from JWT token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.auth import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload and "sub" in payload:
                    return f"user:{payload['sub']}"
            except:
                pass
        
        # Fallback to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _get_limit_config(self, path: str, method: str) -> Dict[str, int]:
        """Get rate limit configuration for endpoint"""
        # Check for exact path match
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for pattern matches
        for pattern, config in self.endpoint_limits.items():
            if pattern != "default" and pattern in path:
                return config
        
        # Apply stricter limits for write operations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return {"limit": self.endpoint_limits["default"]["limit"] // 2, "window": self.endpoint_limits["default"]["window"]}
        
        # Default configuration
        return self.endpoint_limits["default"]


class BurstRateLimitMiddleware(BaseHTTPMiddleware):
    """Burst rate limiting middleware for handling traffic spikes"""
    
    def __init__(self, app, burst_limit: int = None, burst_window: int = 10):
        super().__init__(app)
        self.burst_limit = burst_limit or settings.RATE_LIMIT_BURST
        self.burst_window = burst_window
        self.rate_limiter = InMemoryRateLimiter()  # Use in-memory for burst detection
    
    async def dispatch(self, request: Request, call_next):
        """Apply burst rate limiting"""
        
        # Skip for health checks
        if request.url.path in ["/health", "/docs", "/redoc"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        burst_key = f"burst:{client_id}"
        
        # Check burst limit
        allowed, info = self.rate_limiter.is_allowed(
            burst_key,
            self.burst_limit,
            self.burst_window
        )
        
        if not allowed:
            logger.warning(
                f"Burst limit exceeded for {client_id}",
                extra={
                    "client_id": client_id,
                    "burst_limit": self.burst_limit,
                    "window": self.burst_window
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "BURST_LIMIT_EXCEEDED",
                    "message": "Too many requests in a short time. Please slow down.",
                    "retry_after": info["retry_after"]
                },
                headers={
                    "Retry-After": str(info["retry_after"])
                }
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (same as RateLimitMiddleware)"""
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.auth import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload and "sub" in payload:
                    return f"user:{payload['sub']}"
            except:
                pass
        
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"


def create_rate_limiter():
    """Factory function to create appropriate rate limiter"""
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        return RedisRateLimiter(settings.REDIS_URL)
    else:
        logger.info("Using in-memory rate limiter. Consider using Redis for production.")
        return InMemoryRateLimiter()