"""
Minimal AI CV Agent FastAPI Application
Guaranteed to start on Render
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI CV Agent API is running!",
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "service": "ai-cv-agent-minimal"
    }

@app.get("/api/v1/test")
async def test_api():
    """Test API endpoint"""
    return {
        "message": "API is working!",
        "timestamp": "2025-08-25",
        "environment_vars": {
            "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
            "google_api_key_set": bool(os.getenv("GOOGLE_API_KEY")),
            "port": os.getenv("PORT", "8000")
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting AI CV Agent on port {port}")
    
    uvicorn.run(
        "main-minimal:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
