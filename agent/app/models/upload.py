"""
File upload and parsing models
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ParsedData(BaseModel):
    """Structured data extracted from CV"""
    personal_info: Optional[Dict[str, Any]] = None
    profile: Optional[Dict[str, Any]] = None
    education: Optional[list] = None
    experience: Optional[list] = None
    skills: Optional[list] = None
    certifications: Optional[list] = None
    raw_text: Optional[str] = None


class UploadBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    mime_type: str = Field(default="application/pdf")


class UploadCreate(UploadBase):
    pass


class Upload(UploadBase):
    id: str
    user_id: str
    file_path: str
    status: UploadStatus = UploadStatus.PENDING
    parsed_data: Optional[ParsedData] = None
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ParseRequest(BaseModel):
    """Request to parse an uploaded file"""
    upload_id: str
    extract_structured_data: bool = True


class ParseResponse(BaseModel):
    """Response from parsing operation"""
    success: bool
    parsed_data: Optional[ParsedData] = None
    error: Optional[str] = None
    suggestions: Optional[Dict[str, Any]] = None