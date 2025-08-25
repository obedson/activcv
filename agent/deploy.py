#!/usr/bin/env python3
"""
Deployment script for AI CV Agent
Handles missing dependencies gracefully
"""

import os
import sys

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY", 
        "GOOGLE_API_KEY"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def start_app():
    """Start the application with error handling"""
    try:
        # Try to import the full app first
        from main import app
        print("✅ Full application loaded successfully")
        return app
    except ImportError as e:
        print(f"⚠️  Full app import failed: {e}")
        print("🔄 Falling back to simplified version...")
        
        try:
            from main_deploy import app
            print("✅ Simplified application loaded successfully")
            return app
        except ImportError as e2:
            print(f"❌ Simplified app import failed: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting AI CV Agent deployment...")
    
    if not check_environment():
        print("💡 Please set the required environment variables")
        sys.exit(1)
    
    app = start_app()
    
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    
    print(f"🌐 Starting server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
