"""
Cover letter data models
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class CoverLetterStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CoverLetterTone(str, Enum):
    PROFESSIONAL = "professional"
    MODERN = "modern"
    FORMAL = "formal"
    CASUAL = "casual"
    ACADEMIC = "academic"
    PERSUASIVE = "persuasive"


class CoverLetterCustomizations(BaseModel):
    """Customizations for cover letter generation"""
    hiring_manager: Optional[str] = Field(None, max_length=200)
    company_address: Optional[str] = Field(None, max_length=500)
    position_reference: Optional[str] = Field(None, max_length=200)
    specific_requirements: Optional[str] = Field(None, max_length=1000)
    company_research: Optional[str] = Field(None, max_length=1000)
    personal_connection: Optional[str] = Field(None, max_length=500)
    salary_expectations: Optional[str] = Field(None, max_length=200)
    availability: Optional[str] = Field(None, max_length=200)
    additional_notes: Optional[str] = Field(None, max_length=1000)


class CoverLetterBase(BaseModel):
    template_used: str = "professional_standard"
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    customizations: Optional[CoverLetterCustomizations] = None
    generation_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CoverLetterCreate(CoverLetterBase):
    user_id: str
    job_id: str
    pdf_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    word_count: Optional[int] = None
    content_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CoverLetter(CoverLetterBase):
    id: str
    user_id: str
    job_id: str
    status: CoverLetterStatus = CoverLetterStatus.PENDING
    pdf_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    word_count: Optional[int] = None
    content_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error_message: Optional[str] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoverLetterWithJob(CoverLetter):
    job: Optional[Dict[str, Any]] = None


class CoverLetterGenerationRequest(BaseModel):
    """Request for cover letter generation"""
    job_id: str
    template_key: str = "professional_standard"
    customizations: Optional[CoverLetterCustomizations] = None
    max_length: int = Field(400, ge=200, le=800)


class CoverLetterGenerationResponse(BaseModel):
    """Response for cover letter generation"""
    success: bool
    template_used: str
    generation_metadata: Dict[str, Any]
    content_summary: Dict[str, Any]
    error_message: Optional[str] = None


class CoverLetterPreviewRequest(BaseModel):
    """Request for cover letter preview"""
    template_key: str = "professional_standard"
    job_title: str
    company_name: str
    customizations: Optional[CoverLetterCustomizations] = None


class CoverLetterTemplateInfo(BaseModel):
    """Cover letter template information"""
    id: str
    name: str
    description: str
    tone: str
    category: str
    preview_url: Optional[str] = None
    is_active: bool = True


class CoverLetterDashboardStats(BaseModel):
    """Statistics for cover letter dashboard"""
    total_cover_letters: int = 0
    cover_letters_this_month: int = 0
    most_used_template: Optional[str] = None
    emails_sent: int = 0
    templates_used: Dict[str, int] = Field(default_factory=dict)
    recent_generations: List[CoverLetter] = Field(default_factory=list)


class CoverLetterBulkGenerationRequest(BaseModel):
    """Request for bulk cover letter generation"""
    job_ids: List[str]
    template_key: str = "professional_standard"
    customizations: Optional[CoverLetterCustomizations] = None


class CoverLetterBulkGenerationResponse(BaseModel):
    """Response for bulk cover letter generation"""
    success: bool
    total_jobs: int
    started_generations: int
    failed_jobs: List[str] = Field(default_factory=list)


class CoverLetterSearchFilters(BaseModel):
    """Filters for searching cover letters"""
    template_used: Optional[str] = None
    status: Optional[CoverLetterStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    job_company: Optional[str] = None