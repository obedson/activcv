"""
AI Service Factory - Choose between different AI service implementations
"""

from enum import Enum
from typing import Union
from app.core.config import settings


class AIServiceType(Enum):
    SIMPLE = "simple"
    LANGCHAIN = "langchain"
    OPENAI_ASSISTANT = "openai_assistant"
    CREWAI = "crewai"  # Keep as option if fixed


def get_ai_service() -> Union[object]:
    """Get the configured AI service instance"""
    
    service_type = getattr(settings, 'AI_SERVICE_TYPE', 'simple').lower()
    
    if service_type == AIServiceType.SIMPLE.value:
        from app.services.simple_ai import simple_ai_service
        return simple_ai_service
    
    elif service_type == AIServiceType.LANGCHAIN.value:
        from app.services.langchain_agents import langchain_ai_service
        return langchain_ai_service
    
    elif service_type == AIServiceType.OPENAI_ASSISTANT.value:
        from app.services.openai_assistant import openai_assistant_service
        return openai_assistant_service
    
    elif service_type == AIServiceType.CREWAI.value:
        try:
            from app.services.crew_agents import crew_service
            return crew_service
        except ImportError:
            # Fallback to simple service if CrewAI has issues
            from app.services.simple_ai import simple_ai_service
            return simple_ai_service
    
    else:
        # Default to simple service
        from app.services.simple_ai import simple_ai_service
        return simple_ai_service


# Global service instance
ai_service = get_ai_service()
