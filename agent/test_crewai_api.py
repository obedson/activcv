#!/usr/bin/env python3
"""
Test script to check what's available in the current CrewAI installation
"""

print("Testing CrewAI API availability...")

try:
    import crewai
    print("✅ CrewAI imported")
    
    # Test core classes
    from crewai import Agent, Task, Crew, Process
    print("✅ Core classes available")
    
    # Test tools
    try:
        from crewai.tools import BaseTool
        print("✅ BaseTool available")
    except ImportError as e:
        print(f"❌ BaseTool not available: {e}")
        
        # Check what's in tools
        try:
            import crewai.tools
            print(f"ℹ️  crewai.tools contents: {dir(crewai.tools)}")
        except Exception as e2:
            print(f"❌ Can't inspect crewai.tools: {e2}")
    
    # Test tool decorator
    try:
        from crewai import tool
        print("✅ @tool decorator available")
    except ImportError as e:
        print(f"❌ @tool decorator not available: {e}")
    
    # Test LLM
    try:
        from crewai import LLM
        print("✅ LLM class available")
    except ImportError as e:
        print(f"❌ LLM class not available: {e}")
    
    # Test agent creation
    try:
        agent = Agent(
            role="Test",
            goal="Test",
            backstory="Test",
            model="gpt-3.5-turbo"
        )
        print("✅ Agent creation works")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        
        # Try without model parameter
        try:
            agent = Agent(
                role="Test",
                goal="Test", 
                backstory="Test"
            )
            print("✅ Agent creation works without model parameter")
        except Exception as e2:
            print(f"❌ Agent creation failed completely: {e2}")

except Exception as e:
    print(f"❌ Major error: {e}")

print("API test completed!")
