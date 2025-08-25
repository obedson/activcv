"""
Job watchlist management service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import Client
from fastapi import HTTPException, status

from app.models.jobs import (
    JobSiteWatchlist,
    JobSiteWatchlistCreate,
    JobSiteWatchlistUpdate,
    Job,
    JobCreate,
    JobUpdate,
    SuggestedJob,
    SuggestedJobCreate,
    SuggestedJobUpdate,
    GeneratedCV,
    GeneratedCVCreate,
    CrawlingLog,
    CrawlingLogCreate,
    JobSearchFilters,
    JobStats,
)


class JobWatchlistService:
    """Service for managing job watchlists and related operations"""
    
    def __init__(self, db: Client):
        self.db = db
    
    # Watchlist management
    async def create_watchlist_site(self, user_id: str, data: JobSiteWatchlistCreate) -> JobSiteWatchlist:
        """Add a new job site to user's watchlist"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        insert_data["filters"] = data.filters.dict()
        
        # Check if site already exists for user
        existing = self.db.table("job_sites_watchlist").select("id").eq("user_id", user_id).eq("site_url", str(data.site_url)).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This job site is already in your watchlist"
            )
        
        result = self.db.table("job_sites_watchlist").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create watchlist entry"
            )
        
        return JobSiteWatchlist(**result.data[0])
    
    async def get_user_watchlist(self, user_id: str) -> List[JobSiteWatchlist]:
        """Get all watchlist sites for a user"""
        result = self.db.table("job_sites_watchlist").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return [JobSiteWatchlist(**item) for item in result.data]
    
    async def get_watchlist_site(self, user_id: str, site_id: str) -> Optional[JobSiteWatchlist]:
        """Get specific watchlist site"""
        result = self.db.table("job_sites_watchlist").select("*").eq("id", site_id).eq("user_id", user_id).execute()
        if result.data:
            return JobSiteWatchlist(**result.data[0])
        return None
    
    async def update_watchlist_site(self, user_id: str, site_id: str, data: JobSiteWatchlistUpdate) -> Optional[JobSiteWatchlist]:
        """Update watchlist site"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return await self.get_watchlist_site(user_id, site_id)
        
        if "filters" in update_data:
            update_data["filters"] = data.filters.dict() if data.filters else {}
        
        result = self.db.table("job_sites_watchlist").update(update_data).eq("id", site_id).eq("user_id", user_id).execute()
        if result.data:
            return JobSiteWatchlist(**result.data[0])
        return None
    
    async def delete_watchlist_site(self, user_id: str, site_id: str) -> bool:
        """Delete watchlist site and all associated jobs"""
        result = self.db.table("job_sites_watchlist").delete().eq("id", site_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    async def update_last_crawled(self, site_id: str) -> bool:
        """Update last crawled timestamp for a site"""
        result = self.db.table("job_sites_watchlist").update({
            "last_crawled_at": datetime.utcnow().isoformat()
        }).eq("id", site_id).execute()
        return len(result.data) > 0
    
    # Job management
    async def create_job(self, data: JobCreate) -> Job:
        """Create a new job entry"""
        insert_data = data.dict()
        
        # Handle datetime serialization
        if insert_data.get("posted_date"):
            insert_data["posted_date"] = data.posted_date.isoformat()
        if insert_data.get("expires_at"):
            insert_data["expires_at"] = data.expires_at.isoformat()
        
        result = self.db.table("jobs").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job entry"
            )
        
        return Job(**result.data[0])
    
    async def upsert_job(self, data: JobCreate) -> Job:
        """Create or update job (based on site_id + external_id)"""
        # Try to find existing job
        existing = None
        if data.external_id:
            result = self.db.table("jobs").select("*").eq("site_id", data.site_id).eq("external_id", data.external_id).execute()
            if result.data:
                existing = result.data[0]
        
        if existing:
            # Update existing job
            update_data = data.dict()
            update_data.pop("site_id", None)  # Don't update site_id
            update_data.pop("external_id", None)  # Don't update external_id
            
            # Handle datetime serialization
            if update_data.get("posted_date"):
                update_data["posted_date"] = data.posted_date.isoformat()
            if update_data.get("expires_at"):
                update_data["expires_at"] = data.expires_at.isoformat()
            
            result = self.db.table("jobs").update(update_data).eq("id", existing["id"]).execute()
            return Job(**result.data[0])
        else:
            # Create new job
            return await self.create_job(data)
    
    async def get_jobs_for_site(self, site_id: str, limit: int = 50) -> List[Job]:
        """Get jobs for a specific watchlist site"""
        result = self.db.table("jobs").select("*").eq("site_id", site_id).order("posted_date", desc=True).limit(limit).execute()
        return [Job(**item) for item in result.data]
    
    async def search_jobs(self, user_id: str, filters: JobSearchFilters) -> List[Job]:
        """Search jobs across user's watchlist sites"""
        # Build query for jobs from user's watchlist sites
        query = self.db.table("jobs").select("""
            *,
            job_sites_watchlist!inner(user_id)
        """).eq("job_sites_watchlist.user_id", user_id)
        
        # Apply filters
        if filters.work_mode:
            query = query.eq("work_mode", filters.work_mode.value)
        if filters.job_type:
            query = query.eq("job_type", filters.job_type.value)
        if filters.location:
            query = query.ilike("location", f"%{filters.location}%")
        if filters.company:
            query = query.ilike("company", f"%{filters.company}%")
        if filters.keywords:
            query = query.or_(f"title.ilike.%{filters.keywords}%,description.ilike.%{filters.keywords}%")
        if filters.posted_after:
            query = query.gte("posted_date", filters.posted_after.isoformat())
        
        # Apply pagination
        query = query.order("posted_date", desc=True).range(filters.offset, filters.offset + filters.limit - 1)
        
        result = query.execute()
        return [Job(**item) for item in result.data]
    
    # Suggested jobs management
    async def create_suggested_job(self, data: SuggestedJobCreate) -> SuggestedJob:
        """Create a job suggestion for a user"""
        insert_data = data.dict()
        insert_data["match_reasons"] = data.match_reasons.dict()
        
        result = self.db.table("suggested_jobs").upsert(insert_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job suggestion"
            )
        
        return SuggestedJob(**result.data[0])
    
    async def get_suggested_jobs(self, user_id: str, limit: int = 20, unviewed_only: bool = False) -> List[SuggestedJob]:
        """Get suggested jobs for a user"""
        query = self.db.table("suggested_jobs").select("""
            *,
            jobs(*)
        """).eq("user_id", user_id)
        
        if unviewed_only:
            query = query.eq("is_viewed", False)
        
        query = query.eq("is_dismissed", False).order("match_score", desc=True).limit(limit)
        
        result = query.execute()
        suggestions = []
        for item in result.data:
            job_data = item.pop("jobs", None)
            suggestion = SuggestedJob(**item)
            if job_data:
                suggestion.job = Job(**job_data)
            suggestions.append(suggestion)
        
        return suggestions
    
    async def update_suggested_job(self, user_id: str, suggestion_id: str, data: SuggestedJobUpdate) -> Optional[SuggestedJob]:
        """Update suggested job (mark as viewed/dismissed)"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("suggested_jobs").update(update_data).eq("id", suggestion_id).eq("user_id", user_id).execute()
        if result.data:
            return SuggestedJob(**result.data[0])
        return None
    
    # Generated CVs management
    async def create_generated_cv(self, data: GeneratedCVCreate) -> GeneratedCV:
        """Create a generated CV record"""
        insert_data = data.dict()
        
        result = self.db.table("generated_cvs").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create generated CV record"
            )
        
        return GeneratedCV(**result.data[0])
    
    async def get_generated_cvs(self, user_id: str, limit: int = 20) -> List[GeneratedCV]:
        """Get generated CVs for a user"""
        result = self.db.table("generated_cvs").select("""
            *,
            jobs(title, company, location)
        """).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        
        cvs = []
        for item in result.data:
            job_data = item.pop("jobs", None)
            cv = GeneratedCV(**item)
            if job_data:
                cv.job = Job(**job_data)
            cvs.append(cv)
        
        return cvs
    
    async def mark_cv_email_sent(self, cv_id: str) -> bool:
        """Mark CV as email sent"""
        result = self.db.table("generated_cvs").update({
            "email_sent": True,
            "email_sent_at": datetime.utcnow().isoformat()
        }).eq("id", cv_id).execute()
        return len(result.data) > 0
    
    # Crawling logs
    async def create_crawling_log(self, data: CrawlingLogCreate) -> CrawlingLog:
        """Create a crawling log entry"""
        insert_data = data.dict()
        
        result = self.db.table("crawling_logs").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create crawling log"
            )
        
        return CrawlingLog(**result.data[0])
    
    async def update_crawling_log(self, log_id: str, status: str, **kwargs) -> bool:
        """Update crawling log with completion data"""
        update_data = {"status": status, "completed_at": datetime.utcnow().isoformat()}
        update_data.update(kwargs)
        
        result = self.db.table("crawling_logs").update(update_data).eq("id", log_id).execute()
        return len(result.data) > 0
    
    async def get_crawling_logs(self, user_id: str, limit: int = 20) -> List[CrawlingLog]:
        """Get crawling logs for user's watchlist sites"""
        result = self.db.table("crawling_logs").select("""
            *,
            job_sites_watchlist!inner(user_id, site_name, site_url)
        """).eq("job_sites_watchlist.user_id", user_id).order("started_at", desc=True).limit(limit).execute()
        
        return [CrawlingLog(**item) for item in result.data]
    
    # Statistics
    async def get_job_stats(self, user_id: str) -> JobStats:
        """Get job statistics for user dashboard"""
        stats = JobStats()
        
        # Watchlist stats
        watchlist_result = self.db.table("job_sites_watchlist").select("id, is_active, last_crawled_at").eq("user_id", user_id).execute()
        stats.total_watchlist_sites = len(watchlist_result.data)
        stats.active_sites = len([site for site in watchlist_result.data if site["is_active"]])
        
        # Get last crawl time
        if watchlist_result.data:
            last_crawls = [site["last_crawled_at"] for site in watchlist_result.data if site["last_crawled_at"]]
            if last_crawls:
                stats.last_crawl = max(datetime.fromisoformat(crawl.replace('Z', '+00:00')) for crawl in last_crawls)
        
        # Job stats (from user's watchlist sites)
        if watchlist_result.data:
            site_ids = [site["id"] for site in watchlist_result.data]
            
            # Total jobs
            jobs_result = self.db.table("jobs").select("id, created_at", count="exact").in_("site_id", site_ids).execute()
            stats.total_jobs_found = jobs_result.count or 0
            
            # New jobs today
            today = datetime.utcnow().date()
            new_jobs_result = self.db.table("jobs").select("id", count="exact").in_("site_id", site_ids).gte("created_at", today.isoformat()).execute()
            stats.new_jobs_today = new_jobs_result.count or 0
        
        # Suggested jobs stats
        suggestions_result = self.db.table("suggested_jobs").select("id, is_viewed", count="exact").eq("user_id", user_id).eq("is_dismissed", False).execute()
        stats.suggested_jobs = suggestions_result.count or 0
        
        unviewed_result = self.db.table("suggested_jobs").select("id", count="exact").eq("user_id", user_id).eq("is_viewed", False).eq("is_dismissed", False).execute()
        stats.unviewed_suggestions = unviewed_result.count or 0
        
        # Generated CVs stats
        cvs_result = self.db.table("generated_cvs").select("id", count="exact").eq("user_id", user_id).execute()
        stats.generated_cvs = cvs_result.count or 0
        
        return stats