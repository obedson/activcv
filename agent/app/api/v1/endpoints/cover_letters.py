"""
Cover letter generation and management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.cover_letter_generator import cover_letter_generator
from app.services.job_watchlist import JobWatchlistService
from app.services.profile import ProfileService
from app.services.email_service import email_service
from app.models.cover_letter import (
    CoverLetter,
    CoverLetterCreate,
    CoverLetterGenerationRequest,
    CoverLetterGenerationResponse,
    CoverLetterPreviewRequest,
    CoverLetterBulkGenerationRequest,
    CoverLetterBulkGenerationResponse,
    CoverLetterSearchFilters,
    CoverLetterTemplateInfo,
    CoverLetterDashboardStats,
    CoverLetterWithJob
)
from app.models.jobs import Job

router = APIRouter()


def get_job_watchlist_service(db: Client = Depends(get_db)) -> JobWatchlistService:
    """Get job watchlist service instance"""
    return JobWatchlistService(db)


def get_profile_service(db: Client = Depends(get_db)) -> ProfileService:
    """Get profile service instance"""
    return ProfileService(db)


@router.get("/templates", response_model=List[CoverLetterTemplateInfo])
async def get_cover_letter_templates(
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get available cover letter templates"""
    try:
        # Get templates from database
        result = db.table("cover_letter_templates").select("*").eq("is_active", True).order("name").execute()
        
        templates = []
        for template_data in result.data:
            templates.append(CoverLetterTemplateInfo(**template_data))
        
        return templates
    
    except Exception as e:
        # Fallback to service templates if database query fails
        service_templates = cover_letter_generator.get_available_templates()
        return [
            CoverLetterTemplateInfo(
                id=key,
                name=template["name"],
                description=template["description"],
                tone=template.get("tone", "professional"),
                category="business",
                preview_url=template.get("preview_url")
            )
            for key, template in service_templates.items()
        ]


@router.post("/generate", response_model=CoverLetterGenerationResponse)
async def generate_cover_letter(
    request: CoverLetterGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Generate a cover letter for a specific job"""
    try:
        # Get services
        job_service = JobWatchlistService(db)
        profile_service = ProfileService(db)
        
        # Verify job exists and user has access
        job_result = db.table("jobs").select("""
            *,
            job_sites_watchlist!inner(user_id)
        """).eq("id", request.job_id).eq("job_sites_watchlist.user_id", current_user).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or access denied"
            )
        
        job = Job(**job_result.data[0])
        
        # Get user's complete profile
        user_profile = await profile_service.get_complete_profile(current_user)
        
        # Add background task for cover letter generation
        background_tasks.add_task(
            _generate_cover_letter_background_task,
            current_user,
            job,
            request,
            user_profile,
            db
        )
        
        return CoverLetterGenerationResponse(
            success=True,
            template_used=request.template_key,
            generation_metadata={
                "status": "processing",
                "job_id": request.job_id,
                "template": request.template_key,
                "started_at": "now"
            },
            content_summary={
                "message": "Cover letter generation started. You will receive an email when it's ready."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start cover letter generation: {str(e)}"
        )


@router.get("/", response_model=List[CoverLetterWithJob])
async def get_cover_letters(
    current_user: str = Depends(get_current_user),
    template_used: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db)
):
    """Get user's cover letters"""
    try:
        query = db.table("cover_letters").select("""
            *,
            jobs(title, company, location)
        """).eq("user_id", current_user)
        
        if template_used:
            query = query.eq("template_used", template_used)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        cover_letters = []
        for item in result.data:
            job_data = item.pop("jobs", None)
            cover_letter = CoverLetterWithJob(**item)
            if job_data:
                cover_letter.job = job_data
            cover_letters.append(cover_letter)
        
        return cover_letters
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cover letters: {str(e)}"
        )


@router.get("/{cover_letter_id}", response_model=CoverLetterWithJob)
async def get_cover_letter(
    cover_letter_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get specific cover letter"""
    try:
        result = db.table("cover_letters").select("""
            *,
            jobs(title, company, location, description)
        """).eq("id", cover_letter_id).eq("user_id", current_user).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )
        
        item = result.data[0]
        job_data = item.pop("jobs", None)
        cover_letter = CoverLetterWithJob(**item)
        if job_data:
            cover_letter.job = job_data
        
        return cover_letter
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cover letter: {str(e)}"
        )


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    cover_letter_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Delete cover letter"""
    try:
        # Verify ownership
        result = db.table("cover_letters").select("id, file_path").eq("id", cover_letter_id).eq("user_id", current_user).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )
        
        cover_letter = result.data[0]
        
        # Delete file from storage if exists
        if cover_letter.get("file_path"):
            try:
                # TODO: Delete from storage service
                pass
            except Exception:
                # Continue with database deletion even if file deletion fails
                pass
        
        # Delete from database
        db.table("cover_letters").delete().eq("id", cover_letter_id).execute()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cover letter: {str(e)}"
        )


@router.post("/preview", response_model=dict)
async def preview_cover_letter(
    request: CoverLetterPreviewRequest,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Generate a preview of cover letter without saving"""
    try:
        # Get user profile for preview
        profile_service = ProfileService(db)
        user_profile = await profile_service.get_complete_profile(current_user)
        
        # Create mock job for preview
        mock_job = {
            "title": request.job_title,
            "company": request.company_name,
            "description": "Sample job description for preview",
            "location": "Sample Location"
        }
        
        # Generate preview content
        preview_html = await cover_letter_generator.generate_preview(
            template_key=request.template_key,
            job_data=mock_job,
            user_profile=user_profile,
            customizations=request.customizations
        )
        
        return {
            "success": True,
            "html_preview": preview_html,
            "template_used": request.template_key
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.get("/stats", response_model=CoverLetterDashboardStats)
async def get_cover_letter_stats(
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get cover letter statistics for dashboard"""
    try:
        # Get basic stats
        total_result = db.table("cover_letters").select("id", count="exact").eq("user_id", current_user).execute()
        total_count = total_result.count or 0
        
        # Get this month's stats
        from datetime import datetime, timedelta
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_result = db.table("cover_letters").select("id", count="exact").eq("user_id", current_user).gte("created_at", month_start.isoformat()).execute()
        month_count = month_result.count or 0
        
        # Get template usage stats
        template_result = db.table("cover_letters").select("template_used").eq("user_id", current_user).execute()
        template_usage = {}
        most_used_template = None
        max_usage = 0
        
        for item in template_result.data:
            template = item["template_used"]
            template_usage[template] = template_usage.get(template, 0) + 1
            if template_usage[template] > max_usage:
                max_usage = template_usage[template]
                most_used_template = template
        
        # Get emails sent count
        email_result = db.table("cover_letters").select("id", count="exact").eq("user_id", current_user).eq("email_sent", True).execute()
        emails_sent = email_result.count or 0
        
        # Get recent generations
        recent_result = db.table("cover_letters").select("*").eq("user_id", current_user).order("created_at", desc=True).limit(5).execute()
        recent_generations = [CoverLetter(**item) for item in recent_result.data]
        
        return CoverLetterDashboardStats(
            total_cover_letters=total_count,
            cover_letters_this_month=month_count,
            most_used_template=most_used_template,
            emails_sent=emails_sent,
            templates_used=template_usage,
            recent_generations=recent_generations
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# Background task functions

async def _generate_cover_letter_background_task(
    user_id: str,
    job: Job,
    request: CoverLetterGenerationRequest,
    user_profile: dict,
    db: Client
):
    """Background task for cover letter generation"""
    import time
    start_time = time.time()
    
    try:
        # Generate cover letter
        result = await cover_letter_generator.generate_cover_letter(
            job_data=job.dict(),
            user_profile=user_profile,
            template_key=request.template_key,
            customizations=request.customizations,
            max_length=request.max_length
        )
        
        generation_time = int((time.time() - start_time) * 1000)
        
        # Save to database
        cover_letter_data = {
            "user_id": user_id,
            "job_id": job.id,
            "template_used": request.template_key,
            "pdf_url": result.get("pdf_url"),
            "file_path": result.get("file_path"),
            "file_size": result.get("file_size"),
            "generation_metadata": result.get("metadata", {}),
            "content_data": result.get("content", {})
        }
        
        cover_letter_result = db.table("cover_letters").insert(cover_letter_data).execute()
        
        # Save generation stats
        stats_data = {
            "user_id": user_id,
            "template_id": request.template_key,
            "job_id": job.id,
            "generation_time_ms": generation_time,
            "word_count": result.get("word_count", 0),
            "success": True
        }
        
        db.table("cover_letter_stats").insert(stats_data).execute()
        
        # Send notification email
        if cover_letter_result.data:
            await email_service.send_cover_letter_ready_notification(
                user_id=user_id,
                job_title=job.title,
                company_name=job.company,
                cover_letter_url=result.get("pdf_url")
            )
        
    except Exception as e:
        # Log error and save failed stats
        generation_time = int((time.time() - start_time) * 1000)
        
        stats_data = {
            "user_id": user_id,
            "template_id": request.template_key,
            "job_id": job.id,
            "generation_time_ms": generation_time,
            "word_count": 0,
            "success": False,
            "error_message": str(e)
        }
        
        db.table("cover_letter_stats").insert(stats_data).execute()