#!/usr/bin/env python3
"""
Test script for CrewAI 0.80.0 API structure
"""

print("Testing CrewAI 0.80.0 imports...")

try:
    import crewai
    print(f"SUCCESS: CrewAI imported")
    
    # Test core classes
    from crewai import Agent, Task, Crew, Process
    print("SUCCESS: Core classes imported")
    
    # Test tool approaches
    try:
        from crewai.tools import BaseTool
        print("SUCCESS: BaseTool available")
    except ImportError:
        print("INFO: BaseTool not available")
    
    try:
        from crewai import tool
        print("SUCCESS: @tool decorator available")
    except ImportError:
        print("INFO: @tool decorator not available")
    
    # Test LLM approaches
    try:
        from crewai import LLM
        print("SUCCESS: CrewAI LLM class available")
    except ImportError:
        print("INFO: CrewAI LLM class not available")
    
    print("CrewAI 0.80.0 API test completed!")
    
except Exception as e:
    print(f"ERROR: {e}")
