"""
CrewAI agents for intelligent CV processing and generation
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai import tool
from langchain_openai import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


@tool("cv_analysis_tool")
def cv_analysis_tool(cv_content: str, job_description: str = "") -> str:
    """Analyzes CV content for completeness, relevance, and optimization opportunities"""
    analysis = {
        "completeness_score": _assess_completeness(cv_content),
        "keyword_matches": _extract_keywords(cv_content, job_description),
        "improvement_suggestions": _generate_suggestions(cv_content),
        "ats_compatibility": _check_ats_compatibility(cv_content)
    }
    return str(analysis)


def _assess_completeness(content: str) -> float:
    """Assess how complete the CV content is"""
    required_sections = ["experience", "education", "skills", "contact"]
    found_sections = sum(1 for section in required_sections if section.lower() in content.lower())
    return found_sections / len(required_sections)


def _extract_keywords(cv_content: str, job_description: str) -> List[str]:
    """Extract matching keywords between CV and job description"""
    if not job_description:
        return []
    
    # Simple keyword extraction (in production, use more sophisticated NLP)
    cv_words = set(cv_content.lower().split())
    job_words = set(job_description.lower().split())
    
    # Filter out common words and find matches
    common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
    matches = (cv_words & job_words) - common_words
    
    return list(matches)


def _generate_suggestions(content: str) -> List[str]:
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


def _check_ats_compatibility(content: str) -> Dict[str, Any]:
    """Check ATS compatibility of the CV"""
    return {
        "has_contact_info": any(keyword in content.lower() for keyword in ["email", "phone", "contact"]),
        "has_clear_sections": any(keyword in content.lower() for keyword in ["experience", "education", "skills"]),
        "length_appropriate": 500 <= len(content) <= 2000,
        "score": 0.8  # Placeholder score
    }


@tool("job_matching_tool")
def job_matching_tool(profile_data: str, job_description: str) -> str:
    """Matches job requirements to user profile and calculates compatibility score"""
    match_score = _calculate_match_score(profile_data, job_description)
    missing_skills = _identify_missing_skills(profile_data, job_description)
    recommendations = _generate_match_recommendations(profile_data, job_description)
    
    result = {
        "match_score": match_score,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "compatibility": "high" if match_score > 0.7 else "medium" if match_score > 0.4 else "low"
    }
    
    return str(result)


def _calculate_match_score(profile: str, job_desc: str) -> float:
    """Calculate how well the profile matches the job"""
    profile_words = set(profile.lower().split())
    job_words = set(job_desc.lower().split())
    
    if not job_words:
        return 0.0
    
    matches = len(profile_words & job_words)
    return min(matches / len(job_words), 1.0)


def _identify_missing_skills(profile: str, job_desc: str) -> List[str]:
    """Identify skills mentioned in job but missing from profile"""
    # This is a simplified implementation
    job_skills = ["python", "javascript", "react", "sql", "aws", "docker"]
    profile_lower = profile.lower()
    
    missing = [skill for skill in job_skills if skill in job_desc.lower() and skill not in profile_lower]
    return missing


def _generate_match_recommendations(profile: str, job_desc: str) -> List[str]:
    """Generate recommendations to improve job match"""
    recommendations = []
    missing_skills = _identify_missing_skills(profile, job_desc)
    
    if missing_skills:
        recommendations.append(f"Consider highlighting these skills: {', '.join(missing_skills[:3])}")
    
    if "experience" not in profile.lower() and "experience" in job_desc.lower():
        recommendations.append("Emphasize relevant work experience")
    
    return recommendations


class CrewAIService:
    """Service for managing CrewAI agents and tasks"""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.tools = [cv_analysis_tool, job_matching_tool]
    
    def _get_llm(self):
        """Get the appropriate LLM based on configuration"""
        if settings.GOOGLE_API_KEY:
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7
            )
        elif settings.OPENAI_API_KEY:
            return OpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7
            )
        else:
            raise ValueError("No API key configured for LLM")
    
    def create_cv_agent(self) -> Agent:
        """Create an agent specialized in CV analysis and generation"""
        return Agent(
            role="CV Specialist",
            goal="Create and optimize professional CVs that match job requirements",
            backstory="""You are an expert CV writer with years of experience in recruitment 
            and career counseling. You understand what employers look for and how to present 
            candidate information in the most compelling way.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True
        )
    
    def create_job_analyst_agent(self) -> Agent:
        """Create an agent specialized in job analysis and matching"""
        return Agent(
            role="Job Market Analyst",
            goal="Analyze job requirements and match them with candidate profiles",
            backstory="""You are a seasoned recruiter who understands job market trends 
            and can quickly identify the key requirements and skills needed for different roles.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True
        )
    
    def create_cover_letter_agent(self) -> Agent:
        """Create an agent specialized in cover letter writing"""
        return Agent(
            role="Cover Letter Writer",
            goal="Write compelling, personalized cover letters that get attention",
            backstory="""You are a professional writer specializing in career communications. 
            You know how to craft engaging cover letters that highlight relevant experience 
            and demonstrate genuine interest in the role.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True
        )
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV for a specific job"""
        cv_agent = self.create_cv_agent()
        job_analyst = self.create_job_analyst_agent()
        
        # Create tasks
        analysis_task = Task(
            description=f"""Analyze the job requirements and identify key skills, 
            experience, and qualifications needed for this role:
            
            Job Title: {job.title}
            Company: {job.company}
            Description: {job.description}
            Requirements: {job.requirements}
            """,
            agent=job_analyst,
            expected_output="Detailed analysis of job requirements and key matching criteria"
        )
        
        cv_task = Task(
            description=f"""Create a tailored CV that highlights the candidate's most 
            relevant experience and skills for this specific job. Use the job analysis 
            to prioritize content and optimize for ATS systems.
            
            Candidate Profile:
            Name: {profile.personal_info.full_name}
            Email: {profile.personal_info.email}
            Experience: {[exp.dict() for exp in profile.experience]}
            Education: {[edu.dict() for edu in profile.education]}
            Skills: {profile.skills}
            """,
            agent=cv_agent,
            expected_output="Professional, tailored CV in structured format",
            context=[analysis_task]
        )
        
        # Create and run crew
        crew = Crew(
            agents=[job_analyst, cv_agent],
            tasks=[analysis_task, cv_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        
        return {
            "cv_content": result,
            "job_analysis": analysis_task.output,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a personalized cover letter"""
        cover_letter_agent = self.create_cover_letter_agent()
        job_analyst = self.create_job_analyst_agent()
        
        # Create tasks
        company_research_task = Task(
            description=f"""Research the company and role to understand their values, 
            culture, and what they're looking for in candidates:
            
            Company: {job.company}
            Job Title: {job.title}
            Job Description: {job.description}
            """,
            agent=job_analyst,
            expected_output="Company insights and role-specific requirements"
        )
        
        cover_letter_task = Task(
            description=f"""Write a compelling cover letter that:
            1. Shows genuine interest in the company and role
            2. Highlights the most relevant experience and achievements
            3. Demonstrates cultural fit and enthusiasm
            4. Is concise but impactful (max 400 words)
            
            Candidate Profile:
            Name: {profile.personal_info.full_name}
            Experience: {[exp.dict() for exp in profile.experience]}
            Skills: {profile.skills}
            """,
            agent=cover_letter_agent,
            expected_output="Professional, personalized cover letter",
            context=[company_research_task]
        )
        
        # Create and run crew
        crew = Crew(
            agents=[job_analyst, cover_letter_agent],
            tasks=[company_research_task, cover_letter_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        
        return {
            "cover_letter": result,
            "company_research": company_research_task.output,
            "generated_at": datetime.utcnow().isoformat()
        }


# Global service instance
crew_service = CrewAIService()
