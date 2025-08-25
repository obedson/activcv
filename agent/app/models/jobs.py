"""
Job watchlist and job data models
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class JobType(str, Enum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class CrawlingStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class JobSiteFilters(BaseModel):
    """Filters for job site crawling"""
    location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    work_mode: Optional[WorkMode] = None
    job_type: Optional[JobType] = None
    keywords: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    experience_level: Optional[str] = None


class JobSiteWatchlistBase(BaseModel):
    site_url: HttpUrl = Field(..., description="URL of the job site to monitor")
    site_name: Optional[str] = Field(None, max_length=200)
    filters: JobSiteFilters = Field(default_factory=JobSiteFilters)
    is_active: bool = True


class JobSiteWatchlistCreate(JobSiteWatchlistBase):
    pass


class JobSiteWatchlistUpdate(BaseModel):
    site_url: Optional[HttpUrl] = None
    site_name: Optional[str] = Field(None, max_length=200)
    filters: Optional[JobSiteFilters] = None
    is_active: Optional[bool] = None


class JobSiteWatchlist(JobSiteWatchlistBase):
    id: str
    user_id: str
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    company: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    work_mode: Optional[WorkMode] = None
    job_type: Optional[JobType] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    compensation: Optional[str] = Field(None, max_length=200)
    job_url: Optional[HttpUrl] = None
    posted_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class JobCreate(JobBase):
    site_id: str
    external_id: Optional[str] = Field(None, max_length=200)
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    company: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    work_mode: Optional[WorkMode] = None
    job_type: Optional[JobType] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    compensation: Optional[str] = Field(None, max_length=200)
    job_url: Optional[HttpUrl] = None
    posted_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


class Job(JobBase):
    id: str
    site_id: str
    external_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatchReasons(BaseModel):
    """Reasons why a job was matched to a user"""
    skill_matches: List[str] = Field(default_factory=list)
    experience_matches: List[str] = Field(default_factory=list)
    location_match: bool = False
    title_similarity: float = 0.0
    description_keywords: List[str] = Field(default_factory=list)


class SuggestedJobBase(BaseModel):
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_reasons: MatchReasons = Field(default_factory=MatchReasons)
    is_viewed: bool = False
    is_dismissed: bool = False


class SuggestedJobCreate(SuggestedJobBase):
    user_id: str
    job_id: str


class SuggestedJobUpdate(BaseModel):
    is_viewed: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class SuggestedJob(SuggestedJobBase):
    id: str
    user_id: str
    job_id: str
    job: Optional[Job] = None  # Populated via join
    created_at: datetime

    class Config:
        from_attributes = True


class GeneratedCVBase(BaseModel):
    template_used: str = "modern_one_page"
    generation_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GeneratedCVCreate(GeneratedCVBase):
    user_id: str
    job_id: str
    pdf_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None


class GeneratedCV(GeneratedCVBase):
    id: str
    user_id: str
    job_id: str
    pdf_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    job: Optional[Job] = None  # Populated via join
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlingLogBase(BaseModel):
    status: CrawlingStatus
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_updated: int = 0
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class CrawlingLogCreate(CrawlingLogBase):
    site_id: str


class CrawlingLog(CrawlingLogBase):
    id: str
    site_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobSearchFilters(BaseModel):
    """Filters for searching jobs"""
    work_mode: Optional[WorkMode] = None
    job_type: Optional[JobType] = None
    location: Optional[str] = None
    company: Optional[str] = None
    keywords: Optional[str] = None
    min_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    posted_after: Optional[datetime] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class JobStats(BaseModel):
    """Statistics for job dashboard"""
    total_watchlist_sites: int = 0
    active_sites: int = 0
    total_jobs_found: int = 0
    new_jobs_today: int = 0
    suggested_jobs: int = 0
    unviewed_suggestions: int = 0
    generated_cvs: int = 0
    last_crawl: Optional[datetime] = None