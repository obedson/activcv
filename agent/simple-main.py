"""
Simple AI CV Agent FastAPI Application
Minimal version for testing core functionality
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="AI CV Agent API",
    description="Intelligent resume assistant for job seekers",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI CV Agent is running!",
        "status": "success",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ai-cv-agent",
        "features": {
            "fastapi": "✅",
            "supabase": "✅",
            "templates": "✅",
            "pdf_generation": "⚠️ (development mode)"
        }
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    try:
        # Test core imports
        import supabase
        import jinja2
        
        return {
            "message": "Core functionality test passed",
            "packages": {
                "supabase": "✅ Available",
                "jinja2": "✅ Available",
                "fastapi": "✅ Running"
            }
        }
    except ImportError as e:
        return {
            "message": "Some packages missing",
            "error": str(e),
            "status": "partial"
        }

if __name__ == "__main__":
    print("🚀 Starting AI CV Agent (Simple Mode)")
    print("=" * 50)
    print("Server will be available at:")
    print("- API: http://localhost:8000")
    print("- Health: http://localhost:8000/health")
    print("- Test: http://localhost:8000/api/v1/test")
    print("- Docs: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        "simple-main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )