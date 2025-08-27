#!/usr/bin/env python3
"""
Test script for latest CrewAI API following troubleshooting guide
"""

import sys
import os

print(f"Python version: {sys.version}")
print("=" * 50)

# Test 1: Basic CrewAI imports
try:
    import crewai
    print("✅ CrewAI imported successfully")
    
    # Check if it has version info
    try:
        print(f"✅ CrewAI version: {crewai.__version__}")
    except AttributeError:
        print("ℹ️  CrewAI version not available")
        
except ImportError as e:
    print(f"❌ CrewAI import failed: {e}")
    sys.exit(1)

# Test 2: Core classes
try:
    from crewai import Agent, Task, Crew, Process
    print("✅ Core CrewAI classes imported")
except ImportError as e:
    print(f"❌ Core classes import failed: {e}")
    sys.exit(1)

# Test 3: Tools
try:
    from crewai.tools import BaseTool
    print("✅ BaseTool imported")
except ImportError as e:
    print(f"❌ BaseTool import failed: {e}")

# Test 4: LLM configuration (should work with LiteLLM)
try:
    # Set a dummy API key for testing
    os.environ['OPENAI_API_KEY'] = 'test-key-for-import-test'
    
    agent = Agent(
        role="Test Agent",
        goal="Test agent creation",
        backstory="This is a test agent",
        model="gpt-3.5-turbo",
        temperature=0.7
    )
    print("✅ Agent creation with LiteLLM config works")
    
except Exception as e:
    print(f"⚠️  Agent creation test failed: {e}")

# Test 5: Our service import
try:
    sys.path.append('.')
    from app.services.crew_agents import CrewAIService, get_crew_service
    print("✅ Our CrewAI service imports successfully")
    
    # Test service creation (without actually calling LLM)
    service = get_crew_service()
    print("✅ CrewAI service instantiation works")
    
except Exception as e:
    print(f"❌ Our service import failed: {e}")

print("=" * 50)
print("Latest CrewAI test completed!")
print("\nIf all tests pass, the deployment should work with CrewAI multi-agent capabilities!")
