"""
API v1 router configuration
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, profiles, uploads, jobs, cover_letters, job_processing, document_vault, job_analysis, metrics

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(cover_letters.router, prefix="/cover-letters", tags=["cover-letters"])
api_router.include_router(job_processing.router, prefix="/job-processing", tags=["job-processing"])
api_router.include_router(document_vault.router, prefix="/document-vault", tags=["document-vault"])
api_router.include_router(job_analysis.router, prefix="/job-analysis", tags=["job-analysis"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])