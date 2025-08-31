"""
AI CV Agent FastAPI Application
Main entry point for the CV generation and tailoring service.
"""

# Suppress cryptography deprecation warnings from PyPDF
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
warnings.filterwarnings("ignore", message=".*ARC4.*", category=DeprecationWarning)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import redis
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import setup_logging
from app.services.background_jobs import start_background_jobs, stop_background_jobs
from app.middleware.security import SecurityMiddleware, CSRFMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging()
    
    # Start background jobs for crawling and matching
    if settings.ENABLE_BACKGROUND_JOBS:
        start_background_jobs()
    
    yield
    
    # Shutdown
    if settings.ENABLE_BACKGROUND_JOBS:
        stop_background_jobs()


app = FastAPI(
    title="AI CV Agent API",
    description="Intelligent resume assistant for job seekers",
    version="0.1.0",
    lifespan=lifespan,
)

# Add security and validation middleware
from app.middleware.validation import InputValidationMiddleware, RequestSanitizerMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware, BurstRateLimitMiddleware

# Add middleware in order (last added = first executed)
app.add_middleware(RequestSanitizerMiddleware)
app.add_middleware(InputValidationMiddleware)
app.add_middleware(BurstRateLimitMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-cv-agent"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with detailed error logging"""
    import traceback
    from app.core.exceptions import AIAgentException
    from app.core.logging import logger
    
    # Log the full exception details
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Handle custom exceptions
    if isinstance(exc, AIAgentException):
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.error_code or "APPLICATION_ERROR",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    # Handle HTTP exceptions
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    # Handle validation errors
    from pydantic import ValidationError
    if isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.errors()
            }
        )
    
    # Generic error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )