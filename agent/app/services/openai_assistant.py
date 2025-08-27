"""
OpenAI Assistant API service for CV processing
Simpler alternative to CrewAI using OpenAI's built-in assistant capabilities
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class OpenAIAssistantService:
    """Service using OpenAI Assistant API for CV and job processing"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key required for this service")
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cv_assistant_id = None
        self.job_assistant_id = None
    
    async def _get_or_create_cv_assistant(self):
        """Get or create CV specialist assistant"""
        if self.cv_assistant_id:
            return self.cv_assistant_id
        
        assistant = await self.client.beta.assistants.create(
            name="CV Specialist",
            instructions="""You are an expert CV writer and career counselor with years of experience 
            in recruitment. You create professional, ATS-optimized CVs that highlight relevant experience 
            and match job requirements. You provide detailed analysis and actionable recommendations.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "code_interpreter"}]
        )
        
        self.cv_assistant_id = assistant.id
        return assistant.id
    
    async def _get_or_create_job_assistant(self):
        """Get or create job matching assistant"""
        if self.job_assistant_id:
            return self.job_assistant_id
        
        assistant = await self.client.beta.assistants.create(
            name="Job Market Analyst",
            instructions="""You are a seasoned recruiter and job market analyst. You analyze job 
            requirements, match candidates to roles, and provide insights on improving job applications. 
            You understand ATS systems and what employers look for.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "code_interpreter"}]
        )
        
        self.job_assistant_id = assistant.id
        return assistant.id
    
    async def _run_assistant_conversation(self, assistant_id: str, message: str) -> str:
        """Run a conversation with an assistant"""
        # Create thread
        thread = await self.client.beta.threads.create()
        
        # Add message
        await self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Run assistant
        run = await self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            await asyncio.sleep(1)
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        # Get response
        messages = await self.client.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[0].content[0].text.value
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV using OpenAI Assistant"""
        assistant_id = await self._get_or_create_cv_assistant()
        
        message = f"""
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
        
        Experience: {json.dumps([exp.dict() for exp in profile.experience], indent=2)}
        Education: {json.dumps([edu.dict() for edu in profile.education], indent=2)}
        Skills: {profile.skills}
        
        Please create a professional CV that:
        1. Highlights the most relevant experience for this specific role
        2. Uses keywords from the job description for ATS optimization
        3. Shows quantifiable achievements where possible
        4. Is well-structured and professional
        5. Matches the job requirements and company culture
        
        Format the CV in a clean, professional structure with clear sections.
        """
        
        cv_content = await self._run_assistant_conversation(assistant_id, message)
        
        return {
            "cv_content": cv_content,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "openai_assistant"
        }
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a cover letter using OpenAI Assistant"""
        assistant_id = await self._get_or_create_cv_assistant()
        
        message = f"""
        Write a compelling cover letter for this job application:
        
        JOB DETAILS:
        Title: {job.title}
        Company: {job.company}
        Description: {job.description}
        
        CANDIDATE PROFILE:
        Name: {profile.personal_info.full_name}
        Experience: {json.dumps([exp.dict() for exp in profile.experience], indent=2)}
        Skills: {profile.skills}
        
        Write a cover letter that:
        1. Shows genuine interest in the company and role
        2. Highlights the most relevant experience and achievements
        3. Demonstrates cultural fit and enthusiasm
        4. Is concise but impactful (max 400 words)
        5. Has a strong opening that grabs attention
        6. Ends with a clear call to action
        
        Make it personal and engaging while maintaining professionalism.
        """
        
        cover_letter = await self._run_assistant_conversation(assistant_id, message)
        
        return {
            "cover_letter": cover_letter,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "openai_assistant"
        }
    
    async def analyze_job_match(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Analyze how well a profile matches a job"""
        assistant_id = await self._get_or_create_job_assistant()
        
        message = f"""
        Analyze how well this candidate matches the job requirements:
        
        JOB DETAILS:
        Title: {job.title}
        Company: {job.company}
        Description: {job.description}
        Requirements: {job.requirements}
        
        CANDIDATE PROFILE:
        Experience: {json.dumps([exp.dict() for exp in profile.experience], indent=2)}
        Education: {json.dumps([edu.dict() for edu in profile.education], indent=2)}
        Skills: {profile.skills}
        
        Provide analysis including:
        1. Overall match score (0-100%)
        2. Matching skills and experience
        3. Missing skills or requirements
        4. Recommendations to improve the application
        5. Likelihood of getting an interview
        
        Be specific and actionable in your recommendations.
        """
        
        analysis = await self._run_assistant_conversation(assistant_id, message)
        
        return {
            "analysis": analysis,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "openai_assistant"
        }


# Global service instance
openai_assistant_service = OpenAIAssistantService()
