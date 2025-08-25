"""
Robust AI CV Agent FastAPI Application
Handles import failures gracefully
"""

import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Try to import app components, fall back gracefully
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError as e:
    print(f"⚠️  Config import failed: {e}")
    CONFIG_LOADED = False
    # Fallback settings
    class Settings:
        ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    settings = Settings()

try:
    from app.api.v1.api import api_router
    API_ROUTER_LOADED = True
except ImportError as e:
    print(f"⚠️  API router import failed: {e}")
    API_ROUTER_LOADED = False

# Create FastAPI app
app = FastAPI(
    title="AI CV Agent API",
    description="Intelligent resume assistant for job seekers",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router if available
if API_ROUTER_LOADED:
    app.include_router(api_router, prefix="/api/v1")
    print("✅ Full API router loaded")
else:
    print("⚠️  Running with minimal endpoints only")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI CV Agent API",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "config_loaded": CONFIG_LOADED,
        "api_router_loaded": API_ROUTER_LOADED
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "service": "ai-cv-agent",
        "environment": settings.ENVIRONMENT,
        "components": {
            "config": CONFIG_LOADED,
            "api_router": API_ROUTER_LOADED
        }
    }

@app.get("/api/v1/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_status": "running",
        "full_features": API_ROUTER_LOADED,
        "environment_check": {
            "supabase_configured": bool(settings.SUPABASE_URL),
            "google_api_configured": bool(settings.GOOGLE_API_KEY)
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting AI CV Agent on port {port}")
    print(f"📊 Config loaded: {CONFIG_LOADED}")
    print(f"🔌 API router loaded: {API_ROUTER_LOADED}")
    
    uvicorn.run(
        "main-robust:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
