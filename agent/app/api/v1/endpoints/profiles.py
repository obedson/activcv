"""
Profile management endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.profile import ProfileService
from app.models.profile import (
    PersonalInfo,
    PersonalInfoCreate,
    PersonalInfoUpdate,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    Education,
    EducationCreate,
    EducationUpdate,
    Experience,
    ExperienceCreate,
    ExperienceUpdate,
    Skill,
    SkillCreate,
    SkillUpdate,
    Certification,
    CertificationCreate,
    CertificationUpdate,
    Referee,
    RefereeCreate,
    RefereeUpdate,
    CompleteProfile,
)

router = APIRouter()


def get_profile_service(db: Client = Depends(get_db)) -> ProfileService:
    """Get profile service instance"""
    return ProfileService(db)


# Personal Info endpoints
@router.get("/personal-info", response_model=PersonalInfo)
async def get_personal_info(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's personal information"""
    personal_info = await service.get_personal_info(current_user)
    if not personal_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal information not found"
        )
    return personal_info


@router.post("/personal-info", response_model=PersonalInfo, status_code=status.HTTP_201_CREATED)
async def create_personal_info(
    data: PersonalInfoCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create user's personal information"""
    try:
        return await service.create_personal_info(current_user, data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create personal information"
        )


@router.put("/personal-info", response_model=PersonalInfo)
async def update_personal_info(
    data: PersonalInfoUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update user's personal information"""
    personal_info = await service.update_personal_info(current_user, data)
    if not personal_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal information not found"
        )
    return personal_info


# Profile endpoints
@router.get("/profile", response_model=Profile)
async def get_profile(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's profile"""
    profile = await service.get_profile(current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.post("/profile", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create user's profile"""
    try:
        return await service.create_profile(current_user, data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create profile"
        )


@router.put("/profile", response_model=Profile)
async def update_profile(
    data: ProfileUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update user's profile"""
    profile = await service.update_profile(current_user, data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


# Education endpoints
@router.get("/education", response_model=List[Education])
async def get_education(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's education records"""
    return await service.get_education(current_user)


@router.post("/education", response_model=Education, status_code=status.HTTP_201_CREATED)
async def create_education(
    data: EducationCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create education record"""
    return await service.create_education(current_user, data)


@router.put("/education/{education_id}", response_model=Education)
async def update_education(
    education_id: int,
    data: EducationUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update education record"""
    education = await service.update_education(current_user, education_id, data)
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    return education


@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(
    education_id: int,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete education record"""
    success = await service.delete_education(current_user, education_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )


# Experience endpoints
@router.get("/experience", response_model=List[Experience])
async def get_experience(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's experience records"""
    return await service.get_experience(current_user)


@router.post("/experience", response_model=Experience, status_code=status.HTTP_201_CREATED)
async def create_experience(
    data: ExperienceCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create experience record"""
    return await service.create_experience(current_user, data)


@router.put("/experience/{experience_id}", response_model=Experience)
async def update_experience(
    experience_id: int,
    data: ExperienceUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update experience record"""
    experience = await service.update_experience(current_user, experience_id, data)
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found"
        )
    return experience


@router.delete("/experience/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    experience_id: int,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete experience record"""
    success = await service.delete_experience(current_user, experience_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found"
        )


# Skills endpoints
@router.get("/skills", response_model=List[Skill])
async def get_skills(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's skills"""
    return await service.get_skills(current_user)


@router.post("/skills", response_model=Skill, status_code=status.HTTP_201_CREATED)
async def create_skill(
    data: SkillCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create skill record"""
    return await service.create_skill(current_user, data)


@router.put("/skills/{skill_id}", response_model=Skill)
async def update_skill(
    skill_id: int,
    data: SkillUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update skill record"""
    skill = await service.update_skill(current_user, skill_id, data)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill record not found"
        )
    return skill


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: int,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete skill record"""
    success = await service.delete_skill(current_user, skill_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill record not found"
        )


# Certifications endpoints
@router.get("/certifications", response_model=List[Certification])
async def get_certifications(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's certifications"""
    return await service.get_certifications(current_user)


@router.post("/certifications", response_model=Certification, status_code=status.HTTP_201_CREATED)
async def create_certification(
    data: CertificationCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create certification record"""
    return await service.create_certification(current_user, data)


@router.put("/certifications/{cert_id}", response_model=Certification)
async def update_certification(
    cert_id: int,
    data: CertificationUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update certification record"""
    certification = await service.update_certification(current_user, cert_id, data)
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification record not found"
        )
    return certification


@router.delete("/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification(
    cert_id: int,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete certification record"""
    success = await service.delete_certification(current_user, cert_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification record not found"
        )


# Referees endpoints
@router.get("/referees", response_model=List[Referee])
async def get_referees(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's referees"""
    return await service.get_referees(current_user)


@router.post("/referees", response_model=Referee, status_code=status.HTTP_201_CREATED)
async def create_referee(
    data: RefereeCreate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Create referee record"""
    return await service.create_referee(current_user, data)


@router.put("/referees/{referee_id}", response_model=Referee)
async def update_referee(
    referee_id: int,
    data: RefereeUpdate,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Update referee record"""
    referee = await service.update_referee(current_user, referee_id, data)
    if not referee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referee record not found"
        )
    return referee


@router.delete("/referees/{referee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_referee(
    referee_id: int,
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete referee record"""
    success = await service.delete_referee(current_user, referee_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referee record not found"
        )


# Complete profile endpoint
@router.get("/complete", response_model=CompleteProfile)
async def get_complete_profile(
    current_user: str = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Get user's complete profile with all sections"""
    return await service.get_complete_profile(current_user)