"""
Profile service for database operations
"""

from typing import List, Optional
from supabase import Client
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


class ProfileService:
    """Service for profile-related database operations"""
    
    def __init__(self, db: Client):
        self.db = db
    
    # Personal Info methods
    async def get_personal_info(self, user_id: str) -> Optional[PersonalInfo]:
        """Get user's personal information"""
        result = self.db.table("core.personal_info").select("*").eq("user_id", user_id).execute()
        if result.data:
            return PersonalInfo(**result.data[0])
        return None
    
    async def create_personal_info(self, user_id: str, data: PersonalInfoCreate) -> PersonalInfo:
        """Create user's personal information"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.personal_info").insert(insert_data).execute()
        return PersonalInfo(**result.data[0])
    
    async def update_personal_info(self, user_id: str, data: PersonalInfoUpdate) -> Optional[PersonalInfo]:
        """Update user's personal information"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return await self.get_personal_info(user_id)
        
        update_data["updated_at"] = "now()"
        result = self.db.table("core.personal_info").update(update_data).eq("user_id", user_id).execute()
        
        if result.data:
            return PersonalInfo(**result.data[0])
        return None
    
    # Profile methods
    async def get_profile(self, user_id: str) -> Optional[Profile]:
        """Get user's profile"""
        result = self.db.table("core.profiles").select("*").eq("user_id", user_id).execute()
        if result.data:
            return Profile(**result.data[0])
        return None
    
    async def create_profile(self, user_id: str, data: ProfileCreate) -> Profile:
        """Create user's profile"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.profiles").insert(insert_data).execute()
        return Profile(**result.data[0])
    
    async def update_profile(self, user_id: str, data: ProfileUpdate) -> Optional[Profile]:
        """Update user's profile"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return await self.get_profile(user_id)
        
        update_data["last_updated"] = "now()"
        result = self.db.table("core.profiles").update(update_data).eq("user_id", user_id).execute()
        
        if result.data:
            return Profile(**result.data[0])
        return None
    
    # Education methods
    async def get_education(self, user_id: str) -> List[Education]:
        """Get user's education records"""
        result = self.db.table("core.education").select("*").eq("user_id", user_id).order("start_date", desc=True).execute()
        return [Education(**item) for item in result.data]
    
    async def create_education(self, user_id: str, data: EducationCreate) -> Education:
        """Create education record"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.education").insert(insert_data).execute()
        return Education(**result.data[0])
    
    async def update_education(self, user_id: str, education_id: int, data: EducationUpdate) -> Optional[Education]:
        """Update education record"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("core.education").update(update_data).eq("id", education_id).eq("user_id", user_id).execute()
        
        if result.data:
            return Education(**result.data[0])
        return None
    
    async def delete_education(self, user_id: str, education_id: int) -> bool:
        """Delete education record"""
        result = self.db.table("core.education").delete().eq("id", education_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    # Experience methods
    async def get_experience(self, user_id: str) -> List[Experience]:
        """Get user's experience records"""
        result = self.db.table("core.experience").select("*").eq("user_id", user_id).order("start_date", desc=True).execute()
        return [Experience(**item) for item in result.data]
    
    async def create_experience(self, user_id: str, data: ExperienceCreate) -> Experience:
        """Create experience record"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.experience").insert(insert_data).execute()
        return Experience(**result.data[0])
    
    async def update_experience(self, user_id: str, experience_id: int, data: ExperienceUpdate) -> Optional[Experience]:
        """Update experience record"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("core.experience").update(update_data).eq("id", experience_id).eq("user_id", user_id).execute()
        
        if result.data:
            return Experience(**result.data[0])
        return None
    
    async def delete_experience(self, user_id: str, experience_id: int) -> bool:
        """Delete experience record"""
        result = self.db.table("core.experience").delete().eq("id", experience_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    # Skills methods
    async def get_skills(self, user_id: str) -> List[Skill]:
        """Get user's skills"""
        result = self.db.table("core.skills").select("*").eq("user_id", user_id).order("name").execute()
        return [Skill(**item) for item in result.data]
    
    async def create_skill(self, user_id: str, data: SkillCreate) -> Skill:
        """Create skill record"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.skills").insert(insert_data).execute()
        return Skill(**result.data[0])
    
    async def update_skill(self, user_id: str, skill_id: int, data: SkillUpdate) -> Optional[Skill]:
        """Update skill record"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("core.skills").update(update_data).eq("id", skill_id).eq("user_id", user_id).execute()
        
        if result.data:
            return Skill(**result.data[0])
        return None
    
    async def delete_skill(self, user_id: str, skill_id: int) -> bool:
        """Delete skill record"""
        result = self.db.table("core.skills").delete().eq("id", skill_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    # Certifications methods
    async def get_certifications(self, user_id: str) -> List[Certification]:
        """Get user's certifications"""
        result = self.db.table("core.certifications").select("*").eq("user_id", user_id).order("issue_date", desc=True).execute()
        return [Certification(**item) for item in result.data]
    
    async def create_certification(self, user_id: str, data: CertificationCreate) -> Certification:
        """Create certification record"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.certifications").insert(insert_data).execute()
        return Certification(**result.data[0])
    
    async def update_certification(self, user_id: str, cert_id: int, data: CertificationUpdate) -> Optional[Certification]:
        """Update certification record"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("core.certifications").update(update_data).eq("id", cert_id).eq("user_id", user_id).execute()
        
        if result.data:
            return Certification(**result.data[0])
        return None
    
    async def delete_certification(self, user_id: str, cert_id: int) -> bool:
        """Delete certification record"""
        result = self.db.table("core.certifications").delete().eq("id", cert_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    # Referees methods
    async def get_referees(self, user_id: str) -> List[Referee]:
        """Get user's referees"""
        result = self.db.table("core.referees").select("*").eq("user_id", user_id).order("name").execute()
        return [Referee(**item) for item in result.data]
    
    async def create_referee(self, user_id: str, data: RefereeCreate) -> Referee:
        """Create referee record"""
        insert_data = data.dict()
        insert_data["user_id"] = user_id
        
        result = self.db.table("core.referees").insert(insert_data).execute()
        return Referee(**result.data[0])
    
    async def update_referee(self, user_id: str, referee_id: int, data: RefereeUpdate) -> Optional[Referee]:
        """Update referee record"""
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        if not update_data:
            return None
        
        result = self.db.table("core.referees").update(update_data).eq("id", referee_id).eq("user_id", user_id).execute()
        
        if result.data:
            return Referee(**result.data[0])
        return None
    
    async def delete_referee(self, user_id: str, referee_id: int) -> bool:
        """Delete referee record"""
        result = self.db.table("core.referees").delete().eq("id", referee_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    # Complete profile method
    async def get_complete_profile(self, user_id: str) -> CompleteProfile:
        """Get user's complete profile with all sections"""
        personal_info = await self.get_personal_info(user_id)
        profile = await self.get_profile(user_id)
        education = await self.get_education(user_id)
        experience = await self.get_experience(user_id)
        skills = await self.get_skills(user_id)
        certifications = await self.get_certifications(user_id)
        referees = await self.get_referees(user_id)
        
        return CompleteProfile(
            personal_info=personal_info,
            profile=profile,
            education=education,
            experience=experience,
            skills=skills,
            certifications=certifications,
            referees=referees,
        )