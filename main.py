#!/usr/bin/env python3
"""
Railway deployment entry point for Activ CV Agent
This file allows Railway to find and run the FastAPI application
"""

import sys
import os
import uvicorn

# Add the agent directory to Python path
agent_dir = os.path.join(os.path.dirname(__file__), 'agent')
sys.path.insert(0, agent_dir)

# Change working directory to agent for relative imports
os.chdir(agent_dir)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
    )
