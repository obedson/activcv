"""
Minimal CrewAI-compatible service without CrewAI dependencies
Provides the same interface but uses simple AI calls
"""

from typing import Dict, Any
from datetime import datetime
from .simple_ai import SimpleAIService

from app.models.profile import CompleteProfile
from app.models.jobs import Job


class CrewAIService:
    """CrewAI-compatible service using simple AI calls"""
    
    def __init__(self):
        self.ai_service = SimpleAIService()
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV for a specific job"""
        return await self.ai_service.generate_tailored_cv(profile, job)
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a personalized cover letter"""
        return await self.ai_service.generate_cover_letter(profile, job)


# Global service instance
crew_service = CrewAIService()
