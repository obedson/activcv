"""
Job description analysis API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.job_description_analyzer import job_description_analyzer
from app.services.profile import ProfileService
from app.models.jobs import Job

router = APIRouter()


def get_profile_service(db: Client = Depends(get_db)) -> ProfileService:
    """Get profile service instance"""
    return ProfileService(db)


@router.post("/analyze/{job_id}")
async def analyze_job_description(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Analyze job description and extract requirements"""
    try:
        # Get job
        job_result = db.table("jobs").select("*").eq("id", job_id).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job = Job(**job_result.data[0])
        
        # Analyze job description
        analysis = await job_description_analyzer.analyze_job_description(job)
        
        return {
            "success": True,
            "job_id": job_id,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze job description: {str(e)}"
        )


@router.post("/tailoring-recommendations/{job_id}")
async def get_tailoring_recommendations(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get CV tailoring recommendations based on job analysis"""
    try:
        # Get job
        job_result = db.table("jobs").select("*").eq("id", job_id).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job = Job(**job_result.data[0])
        
        # Get user profile
        user_profile = await profile_service.get_complete_profile(current_user)
        
        # Analyze job description
        job_analysis = await job_description_analyzer.analyze_job_description(job)
        
        # Generate tailoring recommendations
        recommendations = await job_description_analyzer.generate_tailoring_recommendations(
            job_analysis, user_profile
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "job_analysis": job_analysis,
            "recommendations": [
                {
                    "section": rec.section,
                    "action": rec.action,
                    "content": rec.content,
                    "reason": rec.reason,
                    "priority": rec.priority
                }
                for rec in recommendations
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tailoring recommendations: {str(e)}"
        )


@router.post("/batch-analyze")
async def batch_analyze_jobs(
    job_ids: List[str],
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Analyze multiple job descriptions in batch"""
    try:
        if len(job_ids) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 jobs can be analyzed at once"
            )
        
        results = []
        
        for job_id in job_ids:
            try:
                # Get job
                job_result = db.table("jobs").select("*").eq("id", job_id).execute()
                
                if job_result.data:
                    job = Job(**job_result.data[0])
                    analysis = await job_description_analyzer.analyze_job_description(job)
                    
                    results.append({
                        "job_id": job_id,
                        "success": True,
                        "analysis": analysis
                    })
                else:
                    results.append({
                        "job_id": job_id,
                        "success": False,
                        "error": "Job not found"
                    })
                    
            except Exception as e:
                results.append({
                    "job_id": job_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_jobs": len(job_ids),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch analyze jobs: {str(e)}"
        )


@router.get("/skills-gap/{job_id}")
async def analyze_skills_gap(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Analyze skills gap between user profile and job requirements"""
    try:
        # Get job
        job_result = db.table("jobs").select("*").eq("id", job_id).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job = Job(**job_result.data[0])
        
        # Get user profile
        user_profile = await profile_service.get_complete_profile(current_user)
        
        # Analyze job description
        job_analysis = await job_description_analyzer.analyze_job_description(job)
        
        # Extract required skills
        required_skills = set()
        for category, skills in job_analysis.get("skills", {}).get("technical", {}).items():
            required_skills.update(skill.lower() for skill in skills)
        
        # Extract user skills
        user_skills = set()
        if user_profile.skills:
            user_skills.update(skill.skill_name.lower() for skill in user_profile.skills)
        
        # Calculate gaps and matches
        skill_gaps = list(required_skills - user_skills)
        skill_matches = list(required_skills & user_skills)
        
        # Calculate match percentage
        match_percentage = (len(skill_matches) / len(required_skills) * 100) if required_skills else 100
        
        return {
            "success": True,
            "job_id": job_id,
            "skills_analysis": {
                "required_skills": list(required_skills),
                "user_skills": list(user_skills),
                "skill_matches": skill_matches,
                "skill_gaps": skill_gaps,
                "match_percentage": round(match_percentage, 1),
                "total_required": len(required_skills),
                "total_matched": len(skill_matches),
                "total_gaps": len(skill_gaps)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze skills gap: {str(e)}"
        )


@router.post("/keyword-optimization/{job_id}")
async def get_keyword_optimization(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get ATS keyword optimization suggestions"""
    try:
        # Get job
        job_result = db.table("jobs").select("*").eq("id", job_id).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job = Job(**job_result.data[0])
        
        # Analyze job description
        job_analysis = await job_description_analyzer.analyze_job_description(job)
        
        # Extract ATS keywords
        ats_keywords = job_analysis.get("ats_keywords", [])
        
        # Categorize keywords
        keyword_categories = {
            "high_priority": ats_keywords[:10],  # Top 10 most important
            "medium_priority": ats_keywords[10:25],  # Next 15
            "low_priority": ats_keywords[25:50]  # Remaining
        }
        
        # Generate optimization tips
        optimization_tips = [
            "Include keywords naturally throughout your CV",
            "Use exact keyword phrases from the job description",
            "Include keywords in your professional summary",
            "Match the job title in your CV if applicable",
            "Use industry-standard terminology",
            "Include relevant certifications and technologies",
            "Avoid keyword stuffing - maintain readability"
        ]
        
        return {
            "success": True,
            "job_id": job_id,
            "keyword_optimization": {
                "total_keywords": len(ats_keywords),
                "keyword_categories": keyword_categories,
                "optimization_tips": optimization_tips,
                "ats_score": job_analysis.get("complexity_score", 0.5) * 100
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get keyword optimization: {str(e)}"
        )