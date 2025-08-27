"""
Services package
"""

from .profile import ProfileService
from .upload import UploadService
from .storage import StorageService
from .parser import CVParserService
from .job_watchlist import JobWatchlistService
from .job_crawler import JobCrawlerService
from .job_matcher import JobMatcherService
from .crew_agents import CrewAIService, get_crew_service

# Use lazy loading to avoid import-time errors
crew_service = get_crew_service
from .cv_generator import CVGeneratorService, cv_generator
from .email_service import EmailService, email_service

__all__ = [
    "ProfileService", 
    "UploadService", 
    "StorageService", 
    "CVParserService",
    "JobWatchlistService",
    "JobCrawlerService", 
    "JobMatcherService",
    "CrewAIService",
    "crew_service",
    "CVGeneratorService", 
    "cv_generator",
    "EmailService",
    "email_service"
]