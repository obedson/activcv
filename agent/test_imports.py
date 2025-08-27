#!/usr/bin/env python3
"""
Test script to verify CrewAI imports work correctly
"""

import sys
print(f"Python version: {sys.version}")
print("=" * 50)

try:
    import crewai
    print(f"✅ CrewAI version: {crewai.__version__}")
except ImportError as e:
    print(f"❌ CrewAI import failed: {e}")

try:
    from crewai import Agent, Task, Crew, Process
    print("✅ CrewAI core classes imported successfully")
except ImportError as e:
    print(f"❌ CrewAI core classes import failed: {e}")

try:
    from crewai import tool
    print("✅ CrewAI tool decorator imported successfully")
except ImportError as e:
    print(f"❌ CrewAI tool decorator import failed: {e}")

try:
    from langchain_openai import OpenAI
    print("✅ OpenAI import successful")
except ImportError as e:
    print(f"❌ OpenAI import failed: {e}")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("✅ Google Generative AI import successful")
except ImportError as e:
    print(f"❌ Google Generative AI import failed: {e}")

try:
    # Test the actual service import
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from app.services.crew_agents import CrewAIService, cv_analysis_tool, job_matching_tool
    print("✅ CrewAI service and tools import successful")
except ImportError as e:
    print(f"❌ CrewAI service import failed: {e}")
except Exception as e:
    print(f"⚠️  CrewAI service import had other issues: {e}")

print("=" * 50)
print("Import test completed!")
