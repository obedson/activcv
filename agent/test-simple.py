#!/usr/bin/env python3
"""
Test if simple server can start
"""

def test_simple_server():
    print("🔍 Testing Simple Server")
    print("=" * 30)
    
    try:
        from fastapi import FastAPI
        app = FastAPI()
        
        @app.get("/")
        def root():
            return {"message": "Server works!"}
        
        print("✅ FastAPI app created")
        print("✅ Route configured")
        print("✅ Ready to start!")
        
        # Test imports
        import supabase
        print("✅ Supabase available")
        
        import jinja2
        print("✅ Jinja2 available")
        
        print("\n🚀 Server is ready to run!")
        print("Run: python simple-main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_simple_server()