#!/usr/bin/env python3
"""
Test script to verify CrewAI imports work correctly - Simple version
"""

import sys
print(f"Python version: {sys.version}")
print("=" * 50)

try:
    import crewai
    print(f"SUCCESS: CrewAI version: {crewai.__version__}")
except ImportError as e:
    print(f"FAILED: CrewAI import failed: {e}")
except Exception as e:
    print(f"ERROR: CrewAI import error: {e}")

try:
    from crewai import Agent, Task, Crew, Process
    print("SUCCESS: CrewAI core classes imported")
except ImportError as e:
    print(f"FAILED: CrewAI core classes import failed: {e}")

try:
    from crewai import tool
    print("SUCCESS: CrewAI tool decorator imported")
except ImportError as e:
    print(f"FAILED: CrewAI tool decorator import failed: {e}")

try:
    from crewai.tools import BaseTool
    print("SUCCESS: BaseTool imported")
except ImportError as e:
    print(f"FAILED: BaseTool import failed: {e}")

print("=" * 50)
print("Import test completed!")
