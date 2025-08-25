#!/usr/bin/env python3
"""
Quick status check for AI CV Agent installation
"""

import sys
import os
import subprocess
from pathlib import Path

def check_status():
    print("🔍 AI CV Agent - Quick Status Check")
    print("=" * 40)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check if we're in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"Virtual environment: {'✅ Active' if in_venv else '❌ Not active'}")
    
    # Check key imports
    imports_to_test = [
        ('fastapi', 'FastAPI framework'),
        ('uvicorn', 'ASGI server'),
        ('pydantic', 'Data validation'),
        ('supabase', 'Database client'),
        ('requests', 'HTTP client'),
        ('jinja2', 'Template engine')
    ]
    
    print("\n📦 Package Status:")
    for package, description in imports_to_test:
        try:
            __import__(package)
            print(f"✅ {package:12} - {description}")
        except ImportError:
            print(f"❌ {package:12} - {description} (NOT INSTALLED)")
    
    # Check environment files
    print("\n🔧 Configuration Files:")
    env_files = [
        ('agent/.env', 'Backend environment'),
        ('web/.env.local', 'Frontend environment'),
        ('agent/requirements.txt', 'Python dependencies'),
        ('web/package.json', 'Node.js dependencies')
    ]
    
    for file_path, description in env_files:
        if Path(file_path).exists():
            print(f"✅ {file_path:20} - {description}")
        else:
            print(f"❌ {file_path:20} - {description} (MISSING)")
    
    # Check if we can start the app
    print("\n🚀 Application Test:")
    try:
        from fastapi import FastAPI
        app = FastAPI()
        print("✅ FastAPI app can be created")
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
    
    # Check Node.js status
    print("\n🌐 Frontend Status:")
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
    except:
        print("❌ Node.js not available")
    
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm: {result.stdout.strip()}")
        else:
            print("❌ npm not found")
    except:
        print("❌ npm not available")
    
    # Check if node_modules exists
    if Path('web/node_modules').exists():
        print("✅ Frontend dependencies installed")
    else:
        print("❌ Frontend dependencies not installed")
    
    print("\n" + "=" * 40)
    
    # Summary and recommendations
    if in_venv:
        print("🎉 Backend setup looks good!")
        print("\n📝 To start the backend:")
        print("   cd agent")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        print("   python main.py")
    else:
        print("⚠️  Virtual environment not active")
        print("\n📝 To activate virtual environment:")
        print("   cd agent")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
    
    if Path('web/node_modules').exists():
        print("\n📝 To start the frontend:")
        print("   cd web")
        print("   npm run dev")
    else:
        print("\n📝 To install frontend dependencies:")
        print("   cd web")
        print("   npm install")

if __name__ == "__main__":
    check_status()