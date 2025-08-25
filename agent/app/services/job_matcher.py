"""
Job matching service using AI for semantic matching
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from supabase import Client

from app.models.jobs import (
    Job,
    SuggestedJobCreate,
    MatchReasons,
)
from app.models.profile import CompleteProfile
from app.services.job_watchlist import JobWatchlistService
from app.services.profile import ProfileService
from app.core.config import settings


class JobMatcherService:
    """Service for matching jobs to user profiles using AI"""
    
    def __init__(self, db: Client):
        self.db = db
        self.watchlist_service = JobWatchlistService(db)
        self.profile_service = ProfileService(db)
    
    async def match_jobs_for_user(self, user_id: str, limit: int = 50) -> List[SuggestedJobCreate]:
        """Match jobs to a user's profile and create suggestions"""
        # Get user's complete profile
        user_profile = await self.profile_service.get_complete_profile(user_id)
        
        # Get recent jobs from user's watchlist sites
        recent_jobs = await self._get_recent_jobs_for_user(user_id, limit * 2)  # Get more to filter
        
        suggestions = []
        
        for job in recent_jobs:
            try:
                # Calculate match score and reasons
                match_score, match_reasons = await self._calculate_job_match(user_profile, job)
                
                # Only suggest jobs with decent match scores
                if match_score >= 0.3:  # 30% minimum match
                    suggestion = SuggestedJobCreate(
                        user_id=user_id,
                        job_id=job.id,
                        match_score=match_score,
                        match_reasons=match_reasons
                    )
                    suggestions.append(suggestion)
            
            except Exception as e:
                print(f"Error matching job {job.id}: {e}")
                continue
        
        # Sort by match score and limit results
        suggestions.sort(key=lambda x: x.match_score, reverse=True)
        return suggestions[:limit]
    
    async def match_all_users(self) -> Dict[str, Any]:
        """Run job matching for all users with active watchlists"""
        results = {
            "users_processed": 0,
            "suggestions_created": 0,
            "errors": []
        }
        
        # Get all users with active watchlist sites
        users_result = self.db.table("job_sites_watchlist").select("user_id").eq("is_active", True).execute()
        unique_users = list(set(item["user_id"] for item in users_result.data))
        
        for user_id in unique_users:
            try:
                suggestions = await self.match_jobs_for_user(user_id)
                
                # Create suggestions in database
                for suggestion in suggestions:
                    try:
                        await self.watchlist_service.create_suggested_job(suggestion)
                        results["suggestions_created"] += 1
                    except Exception as e:
                        # Might fail due to duplicate constraint, which is fine
                        if "duplicate" not in str(e).lower():
                            print(f"Error creating suggestion: {e}")
                
                results["users_processed"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "user_id": user_id,
                    "error": str(e)
                })
        
        return results
    
    async def _get_recent_jobs_for_user(self, user_id: str, limit: int) -> List[Job]:
        """Get recent jobs from user's watchlist sites"""
        # Get user's watchlist site IDs
        watchlist_result = self.db.table("job_sites_watchlist").select("id").eq("user_id", user_id).eq("is_active", True).execute()
        site_ids = [site["id"] for site in watchlist_result.data]
        
        if not site_ids:
            return []
        
        # Get recent jobs from these sites
        jobs_result = self.db.table("jobs").select("*").in_("site_id", site_ids).order("created_at", desc=True).limit(limit).execute()
        
        return [Job(**job_data) for job_data in jobs_result.data]
    
    async def _calculate_job_match(self, user_profile: CompleteProfile, job: Job) -> Tuple[float, MatchReasons]:
        """Calculate match score between user profile and job"""
        match_reasons = MatchReasons()
        scores = []
        
        # 1. Skills matching (40% weight)
        skill_score = self._calculate_skill_match(user_profile, job, match_reasons)
        scores.append(("skills", skill_score, 0.4))
        
        # 2. Experience matching (30% weight)
        experience_score = self._calculate_experience_match(user_profile, job, match_reasons)
        scores.append(("experience", experience_score, 0.3))
        
        # 3. Title similarity (20% weight)
        title_score = self._calculate_title_similarity(user_profile, job, match_reasons)
        scores.append(("title", title_score, 0.2))
        
        # 4. Location matching (10% weight)
        location_score = self._calculate_location_match(user_profile, job, match_reasons)
        scores.append(("location", location_score, 0.1))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        
        # Bonus for keyword matches in description
        keyword_bonus = self._calculate_keyword_bonus(user_profile, job, match_reasons)
        total_score = min(1.0, total_score + keyword_bonus)
        
        return total_score, match_reasons
    
    def _calculate_skill_match(self, user_profile: CompleteProfile, job: Job, match_reasons: MatchReasons) -> float:
        """Calculate skill matching score"""
        if not user_profile.skills or not job.description:
            return 0.0
        
        user_skills = [skill.name.lower() for skill in user_profile.skills]
        job_text = (job.description + " " + (job.requirements or "")).lower()
        
        matched_skills = []
        for skill in user_skills:
            if skill in job_text or any(keyword in job_text for keyword in skill.split()):
                matched_skills.append(skill)
        
        match_reasons.skill_matches = matched_skills
        
        if not user_skills:
            return 0.0
        
        return len(matched_skills) / len(user_skills)
    
    def _calculate_experience_match(self, user_profile: CompleteProfile, job: Job, match_reasons: MatchReasons) -> float:
        """Calculate experience matching score"""
        if not user_profile.experience:
            return 0.0
        
        job_text = (job.title + " " + (job.description or "") + " " + (job.requirements or "")).lower()
        
        matched_experiences = []
        for exp in user_profile.experience:
            # Check if job title or company appears in job description
            if exp.title and exp.title.lower() in job_text:
                matched_experiences.append(f"Title: {exp.title}")
            if exp.company and exp.company.lower() in job_text:
                matched_experiences.append(f"Company: {exp.company}")
            
            # Check for similar role keywords
            if exp.description:
                exp_keywords = self._extract_keywords(exp.description)
                for keyword in exp_keywords:
                    if keyword in job_text:
                        matched_experiences.append(f"Experience: {keyword}")
        
        match_reasons.experience_matches = list(set(matched_experiences))
        
        return min(1.0, len(matched_experiences) / 5)  # Normalize to max 5 matches
    
    def _calculate_title_similarity(self, user_profile: CompleteProfile, job: Job, match_reasons: MatchReasons) -> float:
        """Calculate job title similarity"""
        if not user_profile.experience or not job.title:
            return 0.0
        
        job_title_words = set(self._extract_keywords(job.title))
        
        max_similarity = 0.0
        for exp in user_profile.experience:
            if exp.title:
                exp_title_words = set(self._extract_keywords(exp.title))
                if exp_title_words and job_title_words:
                    similarity = len(job_title_words.intersection(exp_title_words)) / len(job_title_words.union(exp_title_words))
                    max_similarity = max(max_similarity, similarity)
        
        match_reasons.title_similarity = max_similarity
        return max_similarity
    
    def _calculate_location_match(self, user_profile: CompleteProfile, job: Job, match_reasons: MatchReasons) -> float:
        """Calculate location matching score"""
        if not job.location:
            return 0.5  # Neutral score for unknown location
        
        job_location = job.location.lower()
        
        # Remote work gets high score
        if 'remote' in job_location:
            match_reasons.location_match = True
            return 1.0
        
        # Check user's location preferences
        if user_profile.personal_info:
            user_location_parts = []
            if user_profile.personal_info.city:
                user_location_parts.append(user_profile.personal_info.city.lower())
            if user_profile.personal_info.country:
                user_location_parts.append(user_profile.personal_info.country.lower())
            
            for location_part in user_location_parts:
                if location_part in job_location:
                    match_reasons.location_match = True
                    return 0.8
        
        return 0.3  # Low score for non-matching location
    
    def _calculate_keyword_bonus(self, user_profile: CompleteProfile, job: Job, match_reasons: MatchReasons) -> float:
        """Calculate bonus score for keyword matches"""
        if not job.description:
            return 0.0
        
        job_text = job.description.lower()
        
        # Extract keywords from user's profile
        profile_keywords = set()
        
        if user_profile.profile and user_profile.profile.summary:
            profile_keywords.update(self._extract_keywords(user_profile.profile.summary))
        
        for exp in user_profile.experience or []:
            if exp.description:
                profile_keywords.update(self._extract_keywords(exp.description))
        
        for edu in user_profile.education or []:
            if edu.field_of_study:
                profile_keywords.update(self._extract_keywords(edu.field_of_study))
        
        # Find matching keywords
        matched_keywords = []
        for keyword in profile_keywords:
            if keyword in job_text:
                matched_keywords.append(keyword)
        
        match_reasons.description_keywords = matched_keywords[:10]  # Limit to top 10
        
        # Bonus up to 0.2 points
        return min(0.2, len(matched_keywords) * 0.02)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []
        
        # Clean and tokenize
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Filter out common words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'this', 'that', 'these', 'those'
        }
        
        keywords = []
        for word in words:
            if len(word) > 2 and word not in stop_words and not word.isdigit():
                keywords.append(word)
        
        return keywords
    
    async def get_job_match_explanation(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Get detailed explanation of why a job was matched to a user"""
        # Get user profile and job
        user_profile = await self.profile_service.get_complete_profile(user_id)
        
        job_result = self.db.table("jobs").select("*").eq("id", job_id).execute()
        if not job_result.data:
            return {"error": "Job not found"}
        
        job = Job(**job_result.data[0])
        
        # Calculate match details
        match_score, match_reasons = await self._calculate_job_match(user_profile, job)
        
        return {
            "job": job.dict(),
            "match_score": match_score,
            "match_reasons": match_reasons.dict(),
            "explanation": {
                "skills": f"Found {len(match_reasons.skill_matches)} matching skills",
                "experience": f"Found {len(match_reasons.experience_matches)} relevant experiences",
                "title_similarity": f"Title similarity: {match_reasons.title_similarity:.2%}",
                "location": "Location matches" if match_reasons.location_match else "Location doesn't match",
                "keywords": f"Found {len(match_reasons.description_keywords)} matching keywords"
            }
        }