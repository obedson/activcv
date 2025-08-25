"""
File upload and parsing endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.upload import UploadService
from app.models.upload import Upload, ParsedData, ParseResponse

router = APIRouter()


def get_upload_service(db: Client = Depends(get_db)) -> UploadService:
    """Get upload service instance"""
    return UploadService(db)


@router.post("/", response_model=Upload, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """
    Upload CV file for parsing
    
    Accepts PDF files up to 50MB in size.
    The file will be automatically parsed to extract structured data.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    return await service.upload_and_parse_cv(current_user, file)


@router.get("/", response_model=List[Upload])
async def get_uploads(
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """Get all uploads for the current user"""
    return await service.get_user_uploads(current_user)


@router.get("/{upload_id}", response_model=Upload)
async def get_upload(
    upload_id: str,
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """Get specific upload by ID"""
    upload = await service.get_upload(current_user, upload_id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    return upload


@router.get("/{upload_id}/parsed-data", response_model=ParsedData)
async def get_parsed_data(
    upload_id: str,
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """Get parsed data from uploaded CV"""
    parsed_data = await service.get_parsed_data(current_user, upload_id)
    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parsed data not found or parsing not completed"
        )
    return parsed_data


@router.get("/{upload_id}/download")
async def download_upload(
    upload_id: str,
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """Get signed download URL for uploaded file"""
    try:
        signed_url = await service.get_download_url(current_user, upload_id)
        return {"download_url": signed_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: str,
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """Delete uploaded file and associated data"""
    success = await service.delete_upload(current_user, upload_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )


@router.post("/{upload_id}/apply-parsed-data", status_code=status.HTTP_200_OK)
async def apply_parsed_data_to_profile(
    upload_id: str,
    current_user: str = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service)
):
    """
    Apply parsed CV data to user's profile
    
    This endpoint takes the parsed data from a CV upload and applies it to
    the user's profile, merging with existing data where appropriate.
    """
    # Get parsed data
    parsed_data = await service.get_parsed_data(current_user, upload_id)
    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parsed data available"
        )
    
    # Implement profile merging logic
    try:
        from app.services.profile import ProfileService
        profile_service = ProfileService(service.db)
        
        # Get current profile data
        current_profile = await profile_service.get_complete_profile(current_user)
        
        # Track changes made
        changes_summary = {
            "personal_info": {"updated": False, "fields": []},
            "profile": {"updated": False, "fields": []},
            "education": {"added": 0, "updated": 0},
            "experience": {"added": 0, "updated": 0},
            "skills": {"added": 0, "updated": 0},
            "certifications": {"added": 0, "updated": 0}
        }
        
        # 1. Merge Personal Information
        if parsed_data.personal_info:
            personal_updates = {}
            
            # Only update fields that are empty or missing in current profile
            if not current_profile.personal_info or not current_profile.personal_info.first_name:
                if parsed_data.personal_info.get('first_name'):
                    personal_updates['first_name'] = parsed_data.personal_info['first_name']
                    changes_summary["personal_info"]["fields"].append("first_name")
            
            if not current_profile.personal_info or not current_profile.personal_info.last_name:
                if parsed_data.personal_info.get('last_name'):
                    personal_updates['last_name'] = parsed_data.personal_info['last_name']
                    changes_summary["personal_info"]["fields"].append("last_name")
            
            if not current_profile.personal_info or not current_profile.personal_info.email:
                if parsed_data.personal_info.get('email'):
                    personal_updates['email'] = parsed_data.personal_info['email']
                    changes_summary["personal_info"]["fields"].append("email")
            
            if not current_profile.personal_info or not current_profile.personal_info.phone:
                if parsed_data.personal_info.get('phone'):
                    personal_updates['phone'] = parsed_data.personal_info['phone']
                    changes_summary["personal_info"]["fields"].append("phone")
            
            if not current_profile.personal_info or not current_profile.personal_info.linkedin_url:
                if parsed_data.personal_info.get('linkedin_url'):
                    personal_updates['linkedin_url'] = parsed_data.personal_info['linkedin_url']
                    changes_summary["personal_info"]["fields"].append("linkedin_url")
            
            if personal_updates:
                await profile_service.update_personal_info(current_user, personal_updates)
                changes_summary["personal_info"]["updated"] = True
        
        # 2. Merge Profile Summary
        if parsed_data.profile and parsed_data.profile.get('summary'):
            if not current_profile.profile or not current_profile.profile.summary:
                await profile_service.update_profile(current_user, {
                    'summary': parsed_data.profile['summary']
                })
                changes_summary["profile"]["updated"] = True
                changes_summary["profile"]["fields"].append("summary")
        
        # 3. Merge Education
        if parsed_data.education:
            for edu_data in parsed_data.education:
                # Check if similar education already exists
                existing_edu = None
                if current_profile.education:
                    for existing in current_profile.education:
                        if (existing.institution and edu_data.get('institution') and 
                            existing.institution.lower() == edu_data['institution'].lower() and
                            existing.degree and edu_data.get('degree') and
                            existing.degree.lower() == edu_data['degree'].lower()):
                            existing_edu = existing
                            break
                
                if not existing_edu:
                    # Add new education entry
                    await profile_service.create_education(current_user, edu_data)
                    changes_summary["education"]["added"] += 1
                else:
                    # Update existing if parsed data has more information
                    updates = {}
                    if not existing_edu.field_of_study and edu_data.get('field_of_study'):
                        updates['field_of_study'] = edu_data['field_of_study']
                    if not existing_edu.start_date and edu_data.get('start_date'):
                        updates['start_date'] = edu_data['start_date']
                    if not existing_edu.end_date and edu_data.get('end_date'):
                        updates['end_date'] = edu_data['end_date']
                    
                    if updates:
                        await profile_service.update_education(current_user, existing_edu.id, updates)
                        changes_summary["education"]["updated"] += 1
        
        # 4. Merge Experience
        if parsed_data.experience:
            for exp_data in parsed_data.experience:
                # Check if similar experience already exists
                existing_exp = None
                if current_profile.experience:
                    for existing in current_profile.experience:
                        if (existing.company and exp_data.get('company') and 
                            existing.company.lower() == exp_data['company'].lower() and
                            existing.title and exp_data.get('title') and
                            existing.title.lower() == exp_data['title'].lower()):
                            existing_exp = existing
                            break
                
                if not existing_exp:
                    # Add new experience entry
                    await profile_service.create_experience(current_user, exp_data)
                    changes_summary["experience"]["added"] += 1
                else:
                    # Update existing if parsed data has more information
                    updates = {}
                    if not existing_exp.description and exp_data.get('description'):
                        updates['description'] = exp_data['description']
                    if not existing_exp.start_date and exp_data.get('start_date'):
                        updates['start_date'] = exp_data['start_date']
                    if not existing_exp.end_date and exp_data.get('end_date'):
                        updates['end_date'] = exp_data['end_date']
                    
                    if updates:
                        await profile_service.update_experience(current_user, existing_exp.id, updates)
                        changes_summary["experience"]["updated"] += 1
        
        # 5. Merge Skills
        if parsed_data.skills:
            existing_skill_names = set()
            if current_profile.skills:
                existing_skill_names = {skill.name.lower() for skill in current_profile.skills}
            
            for skill_data in parsed_data.skills:
                skill_name = skill_data.get('name', '').lower()
                if skill_name and skill_name not in existing_skill_names:
                    await profile_service.create_skill(current_user, skill_data)
                    changes_summary["skills"]["added"] += 1
                    existing_skill_names.add(skill_name)
        
        # 6. Merge Certifications
        if parsed_data.certifications:
            existing_cert_names = set()
            if current_profile.certifications:
                existing_cert_names = {cert.name.lower() for cert in current_profile.certifications}
            
            for cert_data in parsed_data.certifications:
                cert_name = cert_data.get('name', '').lower()
                if cert_name and cert_name not in existing_cert_names:
                    await profile_service.create_certification(current_user, cert_data)
                    changes_summary["certifications"]["added"] += 1
                    existing_cert_names.add(cert_name)
        
        # Mark upload as applied
        await service.mark_upload_as_applied(current_user, upload_id)
        
        return {
            "message": "Profile successfully updated with parsed CV data",
            "success": True,
            "changes_summary": changes_summary,
            "total_changes": (
                len(changes_summary["personal_info"]["fields"]) +
                len(changes_summary["profile"]["fields"]) +
                changes_summary["education"]["added"] +
                changes_summary["education"]["updated"] +
                changes_summary["experience"]["added"] +
                changes_summary["experience"]["updated"] +
                changes_summary["skills"]["added"] +
                changes_summary["certifications"]["added"]
            )
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge profile data: {str(e)}"
        )