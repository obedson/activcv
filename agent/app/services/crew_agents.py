"""
CrewAI agents for intelligent CV processing and generation
Updated for latest CrewAI with LiteLLM (standalone architecture)
Following troubleshooting guide recommendations
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class CVAnalysisTool(BaseTool):
    """Tool for analyzing CV content and structure"""
    name: str = "cv_analysis_tool"
    description: str = "Analyzes CV content for completeness, relevance, and optimization opportunities"

    def _run(self, cv_content: str, job_description: str = "") -> str:
        """Analyze CV content against job requirements"""
        analysis = {
            "completeness_score": self._assess_completeness(cv_content),
            "keyword_matches": self._extract_keywords(cv_content, job_description),
            "improvement_suggestions": self._generate_suggestions(cv_content),
            "ats_compatibility": self._check_ats_compatibility(cv_content)
        }
        return str(analysis)

    def _assess_completeness(self, content: str) -> float:
        """Assess how complete the CV content is"""
        required_sections = ["experience", "education", "skills", "contact"]
        found_sections = sum(1 for section in required_sections if section.lower() in content.lower())
        return found_sections / len(required_sections)

    def _extract_keywords(self, cv_content: str, job_description: str) -> List[str]:
        """Extract matching keywords between CV and job description"""
        if not job_description:
            return []
        
        cv_words = set(cv_content.lower().split())
        job_words = set(job_description.lower().split())
        
        common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        matches = (cv_words & job_words) - common_words
        
        return list(matches)

    def _generate_suggestions(self, content: str) -> List[str]:
        """Generate improvement suggestions for the CV"""
        suggestions = []
        
        if "experience" not in content.lower():
            suggestions.append("Add work experience section")
        if "education" not in content.lower():
            suggestions.append("Include education background")
        if "skills" not in content.lower():
            suggestions.append("Add skills section")
        if len(content) < 500:
            suggestions.append("Expand content with more details")
        
        return suggestions

    def _check_ats_compatibility(self, content: str) -> Dict[str, Any]:
        """Check ATS compatibility of the CV"""
        return {
            "has_contact_info": any(keyword in content.lower() for keyword in ["email", "phone", "contact"]),
            "has_clear_sections": any(keyword in content.lower() for keyword in ["experience", "education", "skills"]),
            "length_appropriate": 500 <= len(content) <= 2000,
            "score": 0.8
        }


class JobMatchingTool(BaseTool):
    """Tool for matching jobs to user profiles"""
    name: str = "job_matching_tool"
    description: str = "Matches job requirements to user profile and calculates compatibility score"

    def _run(self, profile_data: str, job_description: str) -> str:
        """Match job requirements to user profile"""
        match_score = self._calculate_match_score(profile_data, job_description)
        missing_skills = self._identify_missing_skills(profile_data, job_description)
        recommendations = self._generate_match_recommendations(profile_data, job_description)
        
        result = {
            "match_score": match_score,
            "missing_skills": missing_skills,
            "recommendations": recommendations,
            "compatibility": "high" if match_score > 0.7 else "medium" if match_score > 0.4 else "low"
        }
        
        return str(result)

    def _calculate_match_score(self, profile: str, job_desc: str) -> float:
        """Calculate how well the profile matches the job"""
        profile_words = set(profile.lower().split())
        job_words = set(job_desc.lower().split())
        
        if not job_words:
            return 0.0
        
        matches = len(profile_words & job_words)
        return min(matches / len(job_words), 1.0)

    def _identify_missing_skills(self, profile: str, job_desc: str) -> List[str]:
        """Identify skills mentioned in job but missing from profile"""
        job_skills = ["python", "javascript", "react", "sql", "aws", "docker"]
        profile_lower = profile.lower()
        
        missing = [skill for skill in job_skills if skill in job_desc.lower() and skill not in profile_lower]
        return missing

    def _generate_match_recommendations(self, profile: str, job_desc: str) -> List[str]:
        """Generate recommendations to improve job match"""
        recommendations = []
        missing_skills = self._identify_missing_skills(profile, job_desc)
        
        if missing_skills:
            recommendations.append(f"Consider highlighting these skills: {', '.join(missing_skills[:3])}")
        
        if "experience" not in profile.lower() and "experience" in job_desc.lower():
            recommendations.append("Emphasize relevant work experience")
        
        return recommendations


class CrewAIService:
    """Service for managing CrewAI agents and tasks with latest API"""
    
    def __init__(self):
        self.tools = [CVAnalysisTool(), JobMatchingTool()]
    
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
        
        llm_config = self._get_llm_config()
        
        # Create specialized agents
        cv_analyst = Agent(
            role="CV Analysis Expert",
            goal="Analyze job requirements and identify key skills and experiences to highlight",
            backstory="You are an expert CV analyst with years of experience in recruitment and talent acquisition.",
            tools=self.tools,
            verbose=True,
            **llm_config
        )
        
        cv_writer = Agent(
            role="Professional CV Writer",
            goal="Create compelling, ATS-optimized CVs that highlight relevant experience",
            backstory="You are a professional CV writer who specializes in creating tailored CVs that get interviews.",
            verbose=True,
            **llm_config
        )
        
        # Create tasks
        analysis_task = Task(
            description=f"""
            Analyze this job posting and candidate profile:
            
            Job: {job.title} at {job.company}
            Requirements: {job.requirements}
            Description: {job.description}
            
            Candidate Profile:
            Name: {profile.personal_info.full_name}
            Experience: {[exp.dict() for exp in profile.experience]}
            Education: {[edu.dict() for edu in profile.education]}
            Skills: {profile.skills}
            
            Identify:
            1. Key requirements and skills from the job posting
            2. Matching experience and skills from the candidate
            3. Keywords for ATS optimization
            4. Areas to emphasize in the CV
            """,
            agent=cv_analyst,
            expected_output="Detailed analysis of job requirements and candidate match"
        )
        
        cv_creation_task = Task(
            description=f"""
            Based on the analysis, create a professional, tailored CV for {profile.personal_info.full_name} 
            applying for {job.title} at {job.company}.
            
            The CV should:
            1. Highlight the most relevant experience and skills
            2. Use keywords from the job description for ATS optimization
            3. Be professionally formatted and easy to read
            4. Show quantifiable achievements where possible
            5. Be tailored specifically for this role
            
            Include all standard CV sections: contact info, professional summary, experience, education, skills.
            """,
            agent=cv_writer,
            expected_output="Complete, professional CV tailored for the specific job application"
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[cv_analyst, cv_writer],
            tasks=[analysis_task, cv_creation_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            
            return {
                "cv_content": str(result),
                "generated_at": datetime.utcnow().isoformat(),
                "method": "crewai_multi_agent",
                "agents_used": ["cv_analyst", "cv_writer"]
            }
            
        except Exception as e:
            # Fallback to simple generation if crew fails
            return await self._simple_cv_generation(profile, job, str(e))
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a cover letter using CrewAI multi-agent system"""
        
        llm_config = self._get_llm_config()
        
        # Create specialized agents
        company_researcher = Agent(
            role="Company Research Specialist",
            goal="Research companies and understand their culture and values",
            backstory="You are a company research expert who understands corporate culture and what companies look for in candidates.",
            verbose=True,
            **llm_config
        )
        
        cover_letter_writer = Agent(
            role="Cover Letter Writer",
            goal="Write compelling, personalized cover letters that get interviews",
            backstory="You are a professional cover letter writer who creates engaging, personalized letters that showcase candidates perfectly.",
            verbose=True,
            **llm_config
        )
        
        # Create tasks
        research_task = Task(
            description=f"""
            Research {job.company} and analyze the job posting for {job.title}.
            
            Job Description: {job.description}
            Requirements: {job.requirements}
            
            Identify:
            1. Company culture and values
            2. What they're looking for in candidates
            3. Key selling points to emphasize
            4. Tone and style to use in the cover letter
            """,
            agent=company_researcher,
            expected_output="Company research insights and cover letter strategy"
        )
        
        writing_task = Task(
            description=f"""
            Write a compelling cover letter for {profile.personal_info.full_name} applying for {job.title} at {job.company}.
            
            Candidate Profile:
            Experience: {[exp.dict() for exp in profile.experience]}
            Skills: {profile.skills}
            
            The cover letter should:
            1. Show genuine interest in the company and role
            2. Highlight the most relevant experience and achievements
            3. Demonstrate cultural fit and enthusiasm
            4. Be concise but impactful (max 400 words)
            5. Have a strong opening that grabs attention
            6. End with a clear call to action
            
            Make it personal and engaging while maintaining professionalism.
            """,
            agent=cover_letter_writer,
            expected_output="Professional, personalized cover letter"
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[company_researcher, cover_letter_writer],
            tasks=[research_task, writing_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            
            return {
                "cover_letter": str(result),
                "generated_at": datetime.utcnow().isoformat(),
                "method": "crewai_multi_agent",
                "agents_used": ["company_researcher", "cover_letter_writer"]
            }
            
        except Exception as e:
            # Fallback to simple generation if crew fails
            return await self._simple_cover_letter_generation(profile, job, str(e))
    
    async def _simple_cv_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback CV generation if CrewAI fails"""
        return {
            "cv_content": f"Fallback CV for {profile.personal_info.full_name} applying to {job.title} at {job.company}",
            "generated_at": datetime.utcnow().isoformat(),
            "method": "fallback_simple",
            "error": error
        }
    
    async def _simple_cover_letter_generation(self, profile: CompleteProfile, job: Job, error: str) -> Dict[str, Any]:
        """Fallback cover letter generation if CrewAI fails"""
        return {
            "cover_letter": f"Fallback cover letter for {profile.personal_info.full_name} applying to {job.title} at {job.company}",
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
