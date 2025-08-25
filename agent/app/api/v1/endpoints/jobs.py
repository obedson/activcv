"""
Job watchlist and job management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.job_watchlist import JobWatchlistService
from app.services.job_crawler import JobCrawlerService
from app.services.job_matcher import JobMatcherService
from app.models.jobs import (
    JobSiteWatchlist,
    JobSiteWatchlistCreate,
    JobSiteWatchlistUpdate,
    Job,
    SuggestedJob,
    SuggestedJobUpdate,
    GeneratedCV,
    CrawlingLog,
    JobSearchFilters,
    JobStats,
    WorkMode,
    JobType,
)

router = APIRouter()


def get_job_watchlist_service(db: Client = Depends(get_db)) -> JobWatchlistService:
    """Get job watchlist service instance"""
    return JobWatchlistService(db)


def get_job_crawler_service(db: Client = Depends(get_db)) -> JobCrawlerService:
    """Get job crawler service instance"""
    return JobCrawlerService(db)


def get_job_matcher_service(db: Client = Depends(get_db)) -> JobMatcherService:
    """Get job matcher service instance"""
    return JobMatcherService(db)


# Watchlist management endpoints
@router.post("/watchlist", response_model=JobSiteWatchlist, status_code=status.HTTP_201_CREATED)
async def create_watchlist_site(
    data: JobSiteWatchlistCreate,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Add a new job site to user's watchlist"""
    return await service.create_watchlist_site(current_user, data)


@router.get("/watchlist", response_model=List[JobSiteWatchlist])
async def get_watchlist(
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get user's job site watchlist"""
    return await service.get_user_watchlist(current_user)


@router.get("/watchlist/{site_id}", response_model=JobSiteWatchlist)
async def get_watchlist_site(
    site_id: str,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get specific watchlist site"""
    site = await service.get_watchlist_site(current_user, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist site not found"
        )
    return site


@router.put("/watchlist/{site_id}", response_model=JobSiteWatchlist)
async def update_watchlist_site(
    site_id: str,
    data: JobSiteWatchlistUpdate,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Update watchlist site"""
    site = await service.update_watchlist_site(current_user, site_id, data)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist site not found"
        )
    return site


@router.delete("/watchlist/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist_site(
    site_id: str,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Delete watchlist site"""
    success = await service.delete_watchlist_site(current_user, site_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist site not found"
        )


# Job search and browsing endpoints
@router.get("/search", response_model=List[Job])
async def search_jobs(
    current_user: str = Depends(get_current_user),
    work_mode: Optional[WorkMode] = Query(None),
    job_type: Optional[JobType] = Query(None),
    location: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    posted_after: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Search jobs from user's watchlist sites"""
    from datetime import datetime
    
    filters = JobSearchFilters(
        work_mode=work_mode,
        job_type=job_type,
        location=location,
        company=company,
        keywords=keywords,
        posted_after=datetime.fromisoformat(posted_after) if posted_after else None,
        limit=limit,
        offset=offset
    )
    
    return await service.search_jobs(current_user, filters)


@router.get("/stats", response_model=JobStats)
async def get_job_stats(
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get job statistics for user dashboard"""
    return await service.get_job_stats(current_user)


# Suggested jobs endpoints
@router.get("/suggestions", response_model=List[SuggestedJob])
async def get_suggested_jobs(
    current_user: str = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    unviewed_only: bool = Query(False),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get job suggestions for user"""
    return await service.get_suggested_jobs(current_user, limit, unviewed_only)


@router.put("/suggestions/{suggestion_id}", response_model=SuggestedJob)
async def update_suggested_job(
    suggestion_id: str,
    data: SuggestedJobUpdate,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Update suggested job (mark as viewed/dismissed)"""
    suggestion = await service.update_suggested_job(current_user, suggestion_id, data)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    return suggestion


@router.get("/suggestions/{suggestion_id}/explanation")
async def get_job_match_explanation(
    suggestion_id: str,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service),
    matcher_service: JobMatcherService = Depends(get_job_matcher_service)
):
    """Get detailed explanation of job match"""
    # Get the suggestion to find the job ID
    suggestion_result = service.db.table("suggested_jobs").select("job_id").eq("id", suggestion_id).eq("user_id", current_user).execute()
    if not suggestion_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    job_id = suggestion_result.data[0]["job_id"]
    return await matcher_service.get_job_match_explanation(current_user, job_id)


# Generated CVs endpoints
@router.get("/generated-cvs", response_model=List[GeneratedCV])
async def get_generated_cvs(
    current_user: str = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get user's generated CVs"""
    return await service.get_generated_cvs(current_user, limit)


@router.post("/generate-cv/{job_id}")
async def generate_cv_for_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Generate tailored CV for a specific job"""
    # Verify job exists and user has access
    job_result = service.db.table("jobs").select("""
        *,
        job_sites_watchlist!inner(user_id)
    """).eq("id", job_id).eq("job_sites_watchlist.user_id", current_user).execute()
    
    if not job_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or access denied"
        )
    
    # Add CV generation to background tasks
    background_tasks.add_task(
        _generate_cv_background_task,
        current_user,
        job_id,
        service
    )
    
    return {
        "message": "CV generation started. You will receive an email when it's ready.",
        "job_id": job_id
    }


# Crawling management endpoints (admin/manual triggers)
@router.post("/crawl/{site_id}")
async def crawl_site_manually(
    site_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    watchlist_service: JobWatchlistService = Depends(get_job_watchlist_service),
    crawler_service: JobCrawlerService = Depends(get_job_crawler_service)
):
    """Manually trigger crawling for a specific site"""
    # Verify user owns the site
    site = await watchlist_service.get_watchlist_site(current_user, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist site not found"
        )
    
    # Add crawling to background tasks
    background_tasks.add_task(_crawl_site_background_task, site, crawler_service)
    
    return {
        "message": f"Crawling started for {site.site_name or site.site_url}",
        "site_id": site_id
    }


@router.post("/match-jobs")
async def trigger_job_matching(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    matcher_service: JobMatcherService = Depends(get_job_matcher_service)
):
    """Manually trigger job matching for current user"""
    background_tasks.add_task(_match_jobs_background_task, current_user, matcher_service)
    
    return {
        "message": "Job matching started. New suggestions will appear shortly.",
        "user_id": current_user
    }


@router.get("/crawling-logs", response_model=List[CrawlingLog])
async def get_crawling_logs(
    current_user: str = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    service: JobWatchlistService = Depends(get_job_watchlist_service)
):
    """Get crawling logs for user's watchlist sites"""
    return await service.get_crawling_logs(current_user, limit)


# Background task functions
async def _generate_cv_background_task(user_id: str, job_id: str, service: JobWatchlistService):
    """Background task for CV generation"""
    try:
        from app.services.profile import ProfileService
        from app.services.cv_generator import cv_generator
        from app.services.email_service import email_service
        from app.core.database import get_db
        
        # Get user's complete profile
        db = get_db()
        profile_service = ProfileService(db)
        complete_profile = await profile_service.get_complete_profile(user_id)
        
        # Get job details
        job_result = service.db.table("jobs").select("*").eq("id", job_id).execute()
        if not job_result.data:
            raise Exception("Job not found")
        
        from app.models.jobs import Job
        job = Job(**job_result.data[0])
        
        # Generate CV using AI
        cv_result = await cv_generator.generate_cv(
            user_id=user_id,
            user_profile=complete_profile,
            template_key="modern_one_page",
            job=job
        )
        
        if cv_result["success"]:
            # Create CV record in database
            from app.models.jobs import GeneratedCVCreate
            cv_data = GeneratedCVCreate(
                user_id=user_id,
                job_id=job_id,
                pdf_url=cv_result["pdf_url"],
                file_path=cv_result["file_path"],
                file_size=cv_result["file_size"],
                template_used=cv_result["template_used"],
                generation_metadata=cv_result["generation_metadata"]
            )
            
            generated_cv = await service.create_generated_cv(cv_data)
            
            # Send email notification
            user_name = f"{complete_profile.personal_info.first_name} {complete_profile.personal_info.last_name}" if complete_profile.personal_info else "User"
            user_email = complete_profile.personal_info.email if complete_profile.personal_info else None
            
            if user_email:
                await email_service.send_cv_generated_notification(
                    user_email=user_email,
                    user_name=user_name,
                    generated_cv=generated_cv,
                    job=job
                )
            
            print(f"CV generated successfully for user {user_id} and job {job_id}")
        else:
            # Send failure notification
            error_message = cv_result.get("error", "Unknown error occurred")
            
            user_name = f"{complete_profile.personal_info.first_name} {complete_profile.personal_info.last_name}" if complete_profile.personal_info else "User"
            user_email = complete_profile.personal_info.email if complete_profile.personal_info else None
            
            if user_email:
                await email_service.send_cv_generation_failed_notification(
                    user_email=user_email,
                    user_name=user_name,
                    error_message=error_message,
                    job=job
                )
            
            raise Exception(f"CV generation failed: {error_message}")
        
    except Exception as e:
        print(f"Error generating CV: {e}")
        # Log error for monitoring
        import traceback
        traceback.print_exc()


async def _crawl_site_background_task(site: JobSiteWatchlist, crawler_service: JobCrawlerService):
    """Background task for site crawling"""
    try:
        await crawler_service.crawl_site(site)
    except Exception as e:
        print(f"Error crawling site {site.id}: {e}")


async def _match_jobs_background_task(user_id: str, matcher_service: JobMatcherService):
    """Background task for job matching"""
    try:
        suggestions = await matcher_service.match_jobs_for_user(user_id)
        print(f"Created {len(suggestions)} job suggestions for user {user_id}")
    except Exception as e:
        print(f"Error matching jobs for user {user_id}: {e}")