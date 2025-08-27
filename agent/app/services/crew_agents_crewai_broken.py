"""
CrewAI agents for intelligent CV processing and generation
Updated for latest CrewAI API without BaseTool dependency
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from crewai import Agent, Task, Crew, Process

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class CrewAIService:
    """Service for managing CrewAI agents and tasks with latest API"""
    
    def __init__(self):
        pass
    
    def _get_llm_config(self):
        """Get LLM configuration for latest CrewAI with LiteLLM"""
        if settings.GOOGLE_API_KEY:
            return {
                "model": "gemini/gemini-pro",
                "temperature": 0.7
            }
        elif settings.OPENAI_API_KEY:
            return {
                "model": "gpt-3.5-turbo", 
                "temperature": 0.7
            }
        else:
            # Use default configuration - CrewAI will handle API keys via environment
            return {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            }
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV using CrewAI multi-agent system"""
        
        try:
            llm_config = self._get_llm_config()
            
            # Create specialized agents without tools for now
            cv_analyst = Agent(
                role="CV Analysis Expert",
                goal="Analyze job requirements and identify key skills and experiences to highlight",
                backstory="""You are an expert CV analyst with years of experience in recruitment 
                and talent acquisition. You understand what employers look for and how to match 
                candidate profiles to job requirements.""",
                verbose=True,
                **llm_config
            )
            
            cv_writer = Agent(
                role="Professional CV Writer",
                goal="Create compelling, ATS-optimized CVs that highlight relevant experience",
                backstory="""You are a professional CV writer who specializes in creating tailored CVs 
                that get interviews. You know how to present information in a way that appeals to both 
                ATS systems and human recruiters.""",
                verbose=True,
                **llm_config
            )
            
            # Create tasks
            analysis_task = Task(
                description=f"""
                Analyze this job posting and candidate profile to identify the best approach for CV tailoring:
                
                JOB POSTING:
                Title: {job.title}
                Company: {job.company}
                Requirements: {job.requirements}
                Description: {job.description}
                
                CANDIDATE PROFILE:
                Name: {profile.personal_info.full_name}
                Email: {profile.personal_info.email}
                Phone: {profile.personal_info.phone}
                
                Experience:
                {self._format_experience(profile.experience)}
                
                Education:
                {self._format_education(profile.education)}
                
                Skills: {', '.join(profile.skills) if profile.skills else 'Not specified'}
                
                ANALYSIS REQUIRED:
                1. Identify the top 5 most important requirements from the job posting
                2. Match candidate's experience and skills to these requirements
                3. Identify keywords that should be included for ATS optimization
                4. Suggest which experiences should be emphasized most
                5. Recommend the best way to structure the CV for this specific role
                
                Provide a detailed analysis that the CV writer can use to create a targeted CV.
                """,
                agent=cv_analyst,
                expected_output="Detailed analysis of job requirements and candidate match with specific recommendations"
            )
            
            cv_creation_task = Task(
                description=f"""
                Based on the analysis provided, create a professional, tailored CV for {profile.personal_info.full_name} 
                applying for {job.title} at {job.company}.
                
                REQUIREMENTS:
                1. Use the analysis to highlight the most relevant experience and skills
                2. Include keywords from the job description for ATS optimization
                3. Structure the CV professionally with clear sections
                4. Show quantifiable achievements where possible
                5. Tailor the professional summary specifically for this role
                6. Ensure the CV is between 1-2 pages in length
                
                CV SECTIONS TO INCLUDE:
                - Contact Information
                - Professional Summary (tailored to the role)
                - Work Experience (emphasizing relevant roles)
                - Education
                - Skills (prioritizing job-relevant skills)
                - Additional sections if relevant (certifications, projects, etc.)
                
                Format the CV in a clean, professional layout that is both ATS-friendly and visually appealing.
                """,
                agent=cv_writer,
                expected_output="Complete, professional CV tailored specifically for the job application",
                context=[analysis_task]  # Use analysis as context
            )
            
            # Create and execute crew
            crew = Crew(
                agents=[cv_analyst, cv_writer],
                tasks=[analysis_task, cv_creation_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            
            return {
                "cv_content": str(result),
                "generated_at": datetime.utcnow().isoformat(),
                "method": "crewai_multi_agent",
                "agents_used": ["cv_analyst", "cv_writer"],
                "job_title": job.title,
                "company": job.company
            }
            
        except Exception as e:
            # Fallback to simple generation if crew fails
            return await self._simple_cv_generation(profile, job, str(e))
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a cover letter using CrewAI multi-agent system"""
        
        try:
            llm_config = self._get_llm_config()
            
            # Create specialized agents
            company_researcher = Agent(
                role="Company Research Specialist",
                goal="Research companies and understand their culture, values, and what they look for in candidates",
                backstory="""You are a company research expert who understands corporate culture 
                and what companies look for in candidates. You can analyze job postings to understand 
                company values and the ideal candidate profile.""",
                verbose=True,
                **llm_config
            )
            
            cover_letter_writer = Agent(
                role="Cover Letter Writer",
                goal="Write compelling, personalized cover letters that get interviews",
                backstory="""You are a professional cover letter writer who creates engaging, 
                personalized letters that showcase candidates perfectly. You know how to balance 
                professionalism with personality to make candidates stand out.""",
                verbose=True,
                **llm_config
            )
            
            # Create tasks
            research_task = Task(
                description=f"""
                Research and analyze {job.company} and the {job.title} position to develop insights for a cover letter:
                
                JOB INFORMATION:
                Company: {job.company}
                Position: {job.title}
                Description: {job.description}
                Requirements: {job.requirements}
                
                RESEARCH OBJECTIVES:
                1. Analyze the company culture and values based on the job posting
                2. Identify what type of candidate they're looking for
                3. Determine the key selling points that should be emphasized
                4. Suggest the appropriate tone and style for the cover letter
                5. Identify specific aspects of the role that should be addressed
                
                Provide insights that will help create a targeted, compelling cover letter.
                """,
                agent=company_researcher,
                expected_output="Company research insights and cover letter strategy recommendations"
            )
            
            writing_task = Task(
                description=f"""
                Write a compelling cover letter for {profile.personal_info.full_name} applying for 
                {job.title} at {job.company}.
                
                CANDIDATE INFORMATION:
                Name: {profile.personal_info.full_name}
                Experience: {self._format_experience(profile.experience)}
                Skills: {', '.join(profile.skills) if profile.skills else 'Various technical and professional skills'}
                
                COVER LETTER REQUIREMENTS:
                1. Use the research insights to tailor the approach
                2. Show genuine interest in the company and role
                3. Highlight the most relevant experience and achievements
                4. Demonstrate cultural fit and enthusiasm
                5. Be concise but impactful (300-400 words maximum)
                6. Have a strong opening that grabs attention
                7. Include specific examples of relevant accomplishments
                8. End with a clear call to action
                
                Make the cover letter personal and engaging while maintaining professionalism.
                Avoid generic phrases and make it specific to this opportunity.
                """,
                agent=cover_letter_writer,
                expected_output="Professional, personalized cover letter that showcases the candidate effectively",
                context=[research_task]  # Use research as context
            )
            
            # Create and execute crew
            crew = Crew(
                agents=[company_researcher, cover_letter_writer],
                tasks=[research_task, writing_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = crew.kickoff()
            
            return {
                "cover_letter": str(result),
                "generated_at": datetime.utcnow().isoformat(),
                "method": "crewai_multi_agent",
                "agents_used": ["company_researcher", "cover_letter_writer"],
                "job_title": job.title,
                "company": job.company
            }
            
        except Exception as e:
            # Fallback to simple generation if crew fails
            return await self._simple_cover_letter_generation(profile, job, str(e))
    
    def _format_experience(self, experience: List) -> str:
        """Format experience for task descriptions"""
        if not experience:
            return "No work experience provided"
        
        formatted = []
        for exp in experience:
            exp_dict = exp.dict() if hasattr(exp, 'dict') else exp
            formatted.append(f"- {exp_dict.get('title', 'Unknown')} at {exp_dict.get('company', 'Unknown')} ({exp_dict.get('start_date', 'Unknown')} - {exp_dict.get('end_date', 'Present')})")
        
        return '\n'.join(formatted)
    
    def _format_education(self, education: List) -> str:
        """Format education for task descriptions"""
        if not education:
            return "No education information provided"
        
        formatted = []
        for edu in education:
            edu_dict = edu.dict() if hasattr(edu, 'dict') else edu
            formatted.append(f"- {edu_dict.get('degree', 'Unknown')} from {edu_dict.get('institution', 'Unknown')} ({edu_dict.get('graduation_year', 'Unknown')})")
        
        return '\n'.join(formatted)
    
    async def _simple_cv_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback CV generation if CrewAI fails"""
        return {
            "cv_content": f"""
            CV for {profile.personal_info.full_name}
            Applying for: {job.title} at {job.company}
            
            Contact Information:
            Email: {profile.personal_info.email}
            Phone: {profile.personal_info.phone}
            
            Professional Summary:
            Experienced professional seeking the {job.title} position at {job.company}.
            
            Skills: {', '.join(profile.skills) if profile.skills else 'Various professional skills'}
            
            Note: This is a fallback CV generated due to technical issues with the AI system.
            """,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "fallback_simple",
            "error": error
        }
    
    async def _simple_cover_letter_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback cover letter generation if CrewAI fails"""
        return {
            "cover_letter": f"""
            Dear Hiring Manager,
            
            I am writing to express my interest in the {job.title} position at {job.company}.
            
            With my background and skills, I believe I would be a valuable addition to your team.
            
            I look forward to hearing from you.
            
            Best regards,
            {profile.personal_info.full_name}
            
            Note: This is a fallback cover letter generated due to technical issues with the AI system.
            """,
            "generated_at": datetime.utcnow().isoformat(),
            "method": "fallback_simple",
            "error": error
        }


# Global service instance - lazy initialization to avoid import-time errors
crew_service = None

def get_crew_service():
    """Get or create the CrewAI service instance"""
    global crew_service
    if crew_service is None:
        crew_service = CrewAIService()
    return crew_service
