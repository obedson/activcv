"""
Simple AI service using direct LLM calls
Lightweight alternative to CrewAI without complex orchestration
"""

import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from openai import AsyncOpenAI
import google.generativeai as genai

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class SimpleAIService:
    """Simple AI service using direct LLM calls"""
    
    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
    
    async def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call the available LLM with the given prompt"""
        
        if self.openai_client:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        
        elif self.gemini_model:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = self.gemini_model.generate_content(full_prompt)
            return response.text
        
        else:
            raise ValueError("No LLM API key configured")
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV"""
        
        system_prompt = """You are an expert CV writer with years of experience in recruitment. 
        Create professional, ATS-optimized CVs that highlight relevant experience and match job requirements."""
        
        prompt = f"""
        Create a tailored CV for this job application:
        
        JOB DETAILS:
        Title: {job.title}
        Company: {job.company}
        Description: {job.description}
        Requirements: {job.requirements}
        
        CANDIDATE PROFILE:
        Name: {profile.personal_info.full_name}
        Email: {profile.personal_info.email}
        Phone: {profile.personal_info.phone}
        Location: {profile.personal_info.location}
        
        EXPERIENCE:
        {json.dumps([exp.dict() for exp in profile.experience], indent=2)}
        
        EDUCATION:
        {json.dumps([edu.dict() for edu in profile.education], indent=2)}
        
        SKILLS: {', '.join(profile.skills)}
        
        Create a professional CV that:
        1. Highlights the most relevant experience for this role
        2. Uses keywords from the job description for ATS optimization
        3. Shows quantifiable achievements
        4. Is well-structured with clear sections
        5. Matches the job requirements
        
        Format as a complete, professional CV ready for submission.
        """
        
        cv_content = await self._call_llm(prompt, system_prompt)
        
        return {
            "cv_content": cv_content,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "simple_ai"
        }
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a personalized cover letter"""
        
        system_prompt = """You are a professional cover letter writer. Write compelling, 
        personalized cover letters that get interviews."""
        
        prompt = f"""
        Write a cover letter for this job application:
        
        JOB: {job.title} at {job.company}
        DESCRIPTION: {job.description}
        
        CANDIDATE:
        Name: {profile.personal_info.full_name}
        Key Experience: {json.dumps([exp.dict() for exp in profile.experience[:3]], indent=2)}
        Skills: {', '.join(profile.skills[:10])}
        
        Write a cover letter that:
        1. Shows genuine interest in the company and role
        2. Highlights most relevant experience
        3. Demonstrates enthusiasm and cultural fit
        4. Is concise but impactful (max 400 words)
        5. Has a strong opening and compelling closing
        
        Make it personal and engaging while maintaining professionalism.
        """
        
        cover_letter = await self._call_llm(prompt, system_prompt)
        
        return {
            "cover_letter": cover_letter,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "simple_ai"
        }
    
    async def analyze_job_match(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Analyze job match compatibility"""
        
        system_prompt = """You are an expert recruiter and job matching specialist. 
        Analyze candidate-job compatibility and provide actionable insights."""
        
        prompt = f"""
        Analyze how well this candidate matches the job:
        
        JOB: {job.title} at {job.company}
        REQUIREMENTS: {job.requirements}
        DESCRIPTION: {job.description}
        
        CANDIDATE:
        Experience: {json.dumps([exp.dict() for exp in profile.experience], indent=2)}
        Education: {json.dumps([edu.dict() for edu in profile.education], indent=2)}
        Skills: {', '.join(profile.skills)}
        
        Provide analysis in JSON format:
        {{
            "match_score": 0.85,
            "matching_skills": ["skill1", "skill2"],
            "missing_skills": ["skill3", "skill4"],
            "recommendations": ["recommendation1", "recommendation2"],
            "interview_likelihood": "high/medium/low",
            "key_strengths": ["strength1", "strength2"],
            "areas_to_improve": ["area1", "area2"]
        }}
        
        Be specific and actionable in recommendations.
        """
        
        analysis_text = await self._call_llm(prompt, system_prompt)
        
        # Try to parse JSON, fallback to text if parsing fails
        try:
            analysis_data = json.loads(analysis_text)
        except json.JSONDecodeError:
            analysis_data = {"raw_analysis": analysis_text}
        
        return {
            "analysis": analysis_data,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "simple_ai"
        }
    
    async def batch_process_jobs(self, profile: CompleteProfile, jobs: List[Job]) -> List[Dict[str, Any]]:
        """Process multiple jobs in parallel"""
        
        tasks = []
        for job in jobs:
            task = self.analyze_job_match(profile, job)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Add job info to results
        for i, result in enumerate(results):
            result["job_id"] = jobs[i].id
            result["job_title"] = jobs[i].title
            result["company"] = jobs[i].company
        
        return results


# Global service instance
simple_ai_service = SimpleAIService()
