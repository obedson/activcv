"""
Multi-Agent AI Service for CV and Cover Letter Generation
Provides multi-agent robustness without CrewAI dependency issues
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from openai import AsyncOpenAI
import google.generativeai as genai

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class MultiAgentService:
    """Multi-agent service using direct AI calls for robustness"""
    
    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup AI clients based on available API keys"""
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
    
    async def _call_ai_agent(self, role: str, task: str, context: str = "") -> str:
        """Call an AI agent with a specific role and task"""
        
        system_prompt = f"""You are a {role}. {context}
        
Your task: {task}

Provide a detailed, professional response that fulfills your role's expertise."""

        try:
            if self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": task}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            
            elif self.gemini_model:
                response = await asyncio.to_thread(
                    self.gemini_model.generate_content,
                    f"{system_prompt}\n\nUser request: {task}"
                )
                return response.text
            
            else:
                return f"AI service unavailable. Mock response for {role}: {task[:100]}..."
                
        except Exception as e:
            return f"Error from {role}: {str(e)}"
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate tailored CV using multi-agent approach"""
        
        # Agent 1: CV Analyst
        analyst_context = """You are an expert CV analyst with years of experience in recruitment 
        and talent acquisition. You understand what employers look for and how to match 
        candidate profiles to job requirements."""
        
        analyst_task = f"""
        Analyze this job posting and candidate profile:
        
        JOB POSTING:
        Title: {job.title}
        Company: {job.company}
        Requirements: {job.requirements}
        Description: {job.description}
        
        CANDIDATE PROFILE:
        Name: {profile.personal_info.full_name}
        Email: {profile.personal_info.email}
        Experience: {self._format_experience(profile.experience)}
        Education: {self._format_education(profile.education)}
        Skills: {', '.join(profile.skills) if profile.skills else 'Not specified'}
        
        Provide:
        1. Top 5 most important job requirements
        2. How candidate matches these requirements
        3. Keywords for ATS optimization
        4. Which experiences to emphasize
        5. Recommended CV structure
        """
        
        # Agent 2: CV Writer (will use analyst's output)
        writer_context = """You are a professional CV writer who specializes in creating tailored CVs 
        that get interviews. You know how to present information appealingly to both ATS systems 
        and human recruiters."""
        
        try:
            # Run agents sequentially for true multi-agent workflow
            print("🤖 Running CV Analyst Agent...")
            analysis = await self._call_ai_agent("CV Analysis Expert", analyst_task, analyst_context)
            
            print("🤖 Running CV Writer Agent...")
            writer_task = f"""
            Based on this analysis: {analysis}
            
            Create a professional, tailored CV for {profile.personal_info.full_name} applying for 
            {job.title} at {job.company}.
            
            Requirements:
            1. Use the analysis to highlight relevant experience
            2. Include ATS keywords identified in analysis
            3. Professional structure with clear sections
            4. Quantifiable achievements where possible
            5. Tailored professional summary
            
            Include: Contact Info, Professional Summary, Experience, Education, Skills
            """
            
            cv_content = await self._call_ai_agent("Professional CV Writer", writer_task, writer_context)
            
            return {
                "cv_content": cv_content,
                "analysis": analysis,
                "generated_at": datetime.utcnow().isoformat(),
                "method": "multi_agent_sequential",
                "agents_used": ["cv_analyst", "cv_writer"],
                "job_title": job.title,
                "company": job.company
            }
            
        except Exception as e:
            return await self._fallback_cv_generation(profile, job, str(e))
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate cover letter using multi-agent approach"""
        
        # Agent 1: Company Researcher
        researcher_context = """You are a company research expert who understands corporate culture 
        and what companies look for in candidates. You analyze job postings to understand 
        company values and ideal candidate profiles."""
        
        researcher_task = f"""
        Research and analyze {job.company} and the {job.title} position:
        
        Company: {job.company}
        Position: {job.title}
        Description: {job.description}
        Requirements: {job.requirements}
        
        Provide:
        1. Company culture and values analysis
        2. What type of candidate they want
        3. Key selling points to emphasize
        4. Appropriate tone and style
        5. Specific role aspects to address
        """
        
        # Agent 2: Cover Letter Writer
        writer_context = """You are a professional cover letter writer who creates engaging, 
        personalized letters that showcase candidates perfectly. You balance professionalism 
        with personality to make candidates stand out."""
        
        try:
            print("🤖 Running Company Research Agent...")
            research = await self._call_ai_agent("Company Research Specialist", researcher_task, researcher_context)
            
            print("🤖 Running Cover Letter Writer Agent...")
            writer_task = f"""
            Based on this research: {research}
            
            Write a compelling cover letter for {profile.personal_info.full_name} applying for 
            {job.title} at {job.company}.
            
            Candidate Info:
            Experience: {self._format_experience(profile.experience)}
            Skills: {', '.join(profile.skills) if profile.skills else 'Various skills'}
            
            Requirements:
            1. Use research insights for tailoring
            2. Show genuine interest in company/role
            3. Highlight relevant experience
            4. Demonstrate cultural fit
            5. 300-400 words maximum
            6. Strong opening and clear call to action
            """
            
            cover_letter = await self._call_ai_agent("Cover Letter Writer", writer_task, writer_context)
            
            return {
                "cover_letter": cover_letter,
                "research": research,
                "generated_at": datetime.utcnow().isoformat(),
                "method": "multi_agent_sequential",
                "agents_used": ["company_researcher", "cover_letter_writer"],
                "job_title": job.title,
                "company": job.company
            }
            
        except Exception as e:
            return await self._fallback_cover_letter_generation(profile, job, str(e))
    
    def _format_experience(self, experience: List) -> str:
        """Format experience for agent tasks"""
        if not experience:
            return "No work experience provided"
        
        formatted = []
        for exp in experience:
            exp_dict = exp.dict() if hasattr(exp, 'dict') else exp
            formatted.append(f"- {exp_dict.get('title', 'Unknown')} at {exp_dict.get('company', 'Unknown')} ({exp_dict.get('start_date', 'Unknown')} - {exp_dict.get('end_date', 'Present')})")
        
        return '\n'.join(formatted)
    
    def _format_education(self, education: List) -> str:
        """Format education for agent tasks"""
        if not education:
            return "No education information provided"
        
        formatted = []
        for edu in education:
            edu_dict = edu.dict() if hasattr(edu, 'dict') else edu
            formatted.append(f"- {edu_dict.get('degree', 'Unknown')} from {edu_dict.get('institution', 'Unknown')} ({edu_dict.get('graduation_year', 'Unknown')})")
        
        return '\n'.join(formatted)
    
    async def _fallback_cv_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback CV generation"""
        return {
            "cv_content": f"Fallback CV for {profile.personal_info.full_name} - {job.title} at {job.company}",
            "generated_at": datetime.utcnow().isoformat(),
            "method": "fallback",
            "error": error
        }
    
    async def _fallback_cover_letter_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback cover letter generation"""
        return {
            "cover_letter": f"Fallback cover letter for {profile.personal_info.full_name} - {job.title} at {job.company}",
            "generated_at": datetime.utcnow().isoformat(),
            "method": "fallback",
            "error": error
        }


# Create service instance with CrewAI-compatible interface
class CrewAIService(MultiAgentService):
    """CrewAI-compatible interface using robust multi-agent implementation"""
    pass


# Global service instance
crew_service = None

def get_crew_service():
    """Get or create the service instance"""
    global crew_service
    if crew_service is None:
        crew_service = CrewAIService()
    return crew_service
