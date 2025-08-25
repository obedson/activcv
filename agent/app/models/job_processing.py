"""
Job processing models for real-time job queue management
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class JobType(str, Enum):
    CV_GENERATION = "cv_generation"
    COVER_LETTER_GENERATION = "cover_letter_generation"
    JOB_ANALYSIS = "job_analysis"
    BULK_GENERATION = "bulk_generation"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JobProcessingStep(BaseModel):
    """Job processing step model"""
    id: Optional[str] = None
    job_queue_id: str
    step_name: str
    step_order: int
    status: StepStatus = StepStatus.PENDING
    progress_percentage: int = Field(default=0, ge=0, le=100)
    step_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobProcessingLog(BaseModel):
    """Job processing log model"""
    id: Optional[str] = None
    job_queue_id: str
    log_level: LogLevel
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobQueueBase(BaseModel):
    """Base job queue model"""
    job_type: JobType
    priority: int = Field(default=5, ge=1, le=10)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)
    scheduled_at: Optional[datetime] = None


class JobQueueCreate(JobQueueBase):
    """Create job queue model"""
    user_id: str


class JobQueueUpdate(BaseModel):
    """Update job queue model"""
    status: Optional[JobStatus] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class JobQueue(JobQueueBase):
    """Complete job queue model"""
    id: str
    user_id: str
    status: JobStatus = JobStatus.PENDING
    progress_percentage: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = None
    total_steps: int = 1
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobQueueWithSteps(JobQueue):
    """Job queue with processing steps"""
    steps: List[JobProcessingStep] = Field(default_factory=list)
    logs: List[JobProcessingLog] = Field(default_factory=list)


class JobProcessingMetrics(BaseModel):
    """Job processing metrics model"""
    id: Optional[str] = None
    job_type: JobType
    status: JobStatus
    processing_time_ms: Optional[int] = None
    queue_wait_time_ms: Optional[int] = None
    retry_count: int = 0
    error_category: Optional[str] = None
    created_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobDashboardStats(BaseModel):
    """Dashboard statistics for job processing"""
    total_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    avg_processing_time_ms: Optional[float] = None
    avg_queue_wait_time_ms: Optional[float] = None
    success_rate: float = 0.0
    jobs_by_type: Dict[str, int] = Field(default_factory=dict)
    recent_jobs: List[JobQueue] = Field(default_factory=list)


class JobProgressUpdate(BaseModel):
    """Real-time job progress update"""
    job_id: str
    status: JobStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: Optional[str] = None
    step_progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    error: Optional[str] = None
    updated_at: datetime


class BulkJobRequest(BaseModel):
    """Bulk job processing request"""
    job_type: JobType
    jobs: List[Dict[str, Any]] = Field(..., min_items=1, max_items=50)
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)


class BulkJobResponse(BaseModel):
    """Bulk job processing response"""
    success: bool
    total_jobs: int
    created_jobs: List[str] = Field(default_factory=list)
    failed_jobs: List[Dict[str, str]] = Field(default_factory=list)
    batch_id: Optional[str] = None


class JobSearchFilters(BaseModel):
    """Filters for searching jobs"""
    job_type: Optional[JobType] = None
    status: Optional[JobStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    priority_min: Optional[int] = Field(None, ge=1, le=10)
    priority_max: Optional[int] = Field(None, ge=1, le=10)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class JobRetryRequest(BaseModel):
    """Job retry request"""
    job_id: str
    reset_retry_count: bool = False
    new_priority: Optional[int] = Field(None, ge=1, le=10)
    scheduled_at: Optional[datetime] = None


class JobCancellationRequest(BaseModel):
    """Job cancellation request"""
    job_id: str
    reason: Optional[str] = None


# Job processing step definitions
CV_GENERATION_STEPS = [
    {"name": "profile_analysis", "order": 1, "description": "Analyzing user profile"},
    {"name": "job_analysis", "order": 2, "description": "Analyzing job requirements"},
    {"name": "content_generation", "order": 3, "description": "Generating CV content"},
    {"name": "template_application", "order": 4, "description": "Applying template styling"},
    {"name": "pdf_generation", "order": 5, "description": "Generating PDF document"},
    {"name": "quality_check", "order": 6, "description": "Quality assurance check"},
    {"name": "delivery", "order": 7, "description": "Preparing for delivery"}
]

COVER_LETTER_GENERATION_STEPS = [
    {"name": "company_research", "order": 1, "description": "Researching company information"},
    {"name": "profile_analysis", "order": 2, "description": "Analyzing user profile"},
    {"name": "content_generation", "order": 3, "description": "Writing cover letter content"},
    {"name": "template_application", "order": 4, "description": "Applying template formatting"},
    {"name": "pdf_generation", "order": 5, "description": "Generating PDF document"},
    {"name": "quality_review", "order": 6, "description": "Quality review and validation"},
    {"name": "delivery", "order": 7, "description": "Preparing for delivery"}
]

JOB_ANALYSIS_STEPS = [
    {"name": "job_parsing", "order": 1, "description": "Parsing job description"},
    {"name": "requirement_extraction", "order": 2, "description": "Extracting requirements"},
    {"name": "skill_matching", "order": 3, "description": "Matching skills and experience"},
    {"name": "compatibility_scoring", "order": 4, "description": "Calculating compatibility score"},
    {"name": "recommendation_generation", "order": 5, "description": "Generating recommendations"}
]

BULK_GENERATION_STEPS = [
    {"name": "job_validation", "order": 1, "description": "Validating job requests"},
    {"name": "queue_preparation", "order": 2, "description": "Preparing individual jobs"},
    {"name": "batch_processing", "order": 3, "description": "Processing job batch"},
    {"name": "result_compilation", "order": 4, "description": "Compiling results"},
    {"name": "notification", "order": 5, "description": "Sending notifications"}
]

STEP_DEFINITIONS = {
    JobType.CV_GENERATION: CV_GENERATION_STEPS,
    JobType.COVER_LETTER_GENERATION: COVER_LETTER_GENERATION_STEPS,
    JobType.JOB_ANALYSIS: JOB_ANALYSIS_STEPS,
    JobType.BULK_GENERATION: BULK_GENERATION_STEPS
}