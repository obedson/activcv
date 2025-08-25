"""
Profile data models
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class PersonalInfoBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


class PersonalInfoCreate(PersonalInfoBase):
    pass


class PersonalInfoUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


class PersonalInfo(PersonalInfoBase):
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    headline: Optional[str] = Field(None, max_length=200)
    summary: Optional[str] = Field(None, max_length=2000)
    linkedin_url: Optional[str] = Field(None, max_length=200)
    website_url: Optional[str] = Field(None, max_length=200)
    additional_details: Optional[str] = Field(None, max_length=5000)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class Profile(ProfileBase):
    user_id: str
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class EducationBase(BaseModel):
    institution: str = Field(..., min_length=1, max_length=200)
    degree: Optional[str] = Field(None, max_length=100)
    field_of_study: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currently_enrolled: bool = False
    gpa: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=1000)


class EducationCreate(EducationBase):
    pass


class EducationUpdate(EducationBase):
    pass


class Education(EducationBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExperienceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currently_employed: bool = False
    achievements: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, max_length=2000)
    additional_notes: Optional[str] = Field(None, max_length=1000)


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(ExperienceBase):
    pass


class Experience(ExperienceBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|expert)$")
    category: Optional[str] = Field(None, max_length=100)
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    context: Optional[str] = Field(None, max_length=500)


class SkillCreate(SkillBase):
    pass


class SkillUpdate(SkillBase):
    pass


class Skill(SkillBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CertificationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    issuing_organization: Optional[str] = Field(None, max_length=200)
    issue_date: Optional[date] = None
    expiration_date: Optional[date] = None
    credential_id: Optional[str] = Field(None, max_length=100)
    credential_url: Optional[str] = Field(None, max_length=500)


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(CertificationBase):
    pass


class Certification(CertificationBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class RefereeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    relationship: Optional[str] = Field(None, max_length=200)


class RefereeCreate(RefereeBase):
    pass


class RefereeUpdate(RefereeBase):
    pass


class Referee(RefereeBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CompleteProfile(BaseModel):
    """Complete user profile with all sections"""
    personal_info: Optional[PersonalInfo] = None
    profile: Optional[Profile] = None
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    referees: List[Referee] = Field(default_factory=list)