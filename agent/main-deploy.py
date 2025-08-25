"""
AI CV Agent FastAPI Application - Deployment Version
Simplified version for successful deployment
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

# Simple settings class
class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting AI CV Agent...")
    yield
    # Shutdown
    print("🛑 Shutting down AI CV Agent...")

# Create FastAPI app
app = FastAPI(
    title="AI CV Agent API",
    description="Intelligent resume assistant for job seekers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI CV Agent API",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ai-cv-agent",
        "environment": settings.ENVIRONMENT
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "API is working!",
        "supabase_configured": bool(settings.SUPABASE_URL),
        "google_api_configured": bool(settings.GOOGLE_API_KEY)
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main-deploy:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
