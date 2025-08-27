"""
LangChain-based AI service for CV processing and generation
Alternative to CrewAI with similar functionality
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.profile import CompleteProfile
from app.models.jobs import Job


class CVAnalysis(BaseModel):
    """Structured output for CV analysis"""
    completeness_score: float = Field(description="Score from 0-1 indicating CV completeness")
    keyword_matches: List[str] = Field(description="Keywords that match job requirements")
    improvement_suggestions: List[str] = Field(description="Suggestions for CV improvement")
    ats_compatibility_score: float = Field(description="ATS compatibility score 0-1")


class JobMatch(BaseModel):
    """Structured output for job matching"""
    match_score: float = Field(description="Overall match score 0-1")
    missing_skills: List[str] = Field(description="Skills mentioned in job but missing from profile")
    recommendations: List[str] = Field(description="Recommendations to improve match")
    compatibility: str = Field(description="Overall compatibility: high/medium/low")


class LangChainAIService:
    """AI service using LangChain for CV and job processing"""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.cv_analysis_parser = PydanticOutputParser(pydantic_object=CVAnalysis)
        self.job_match_parser = PydanticOutputParser(pydantic_object=JobMatch)
    
    def _get_llm(self):
        """Get the appropriate LLM based on configuration"""
        if settings.GOOGLE_API_KEY:
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7
            )
        elif settings.OPENAI_API_KEY:
            return ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
        else:
            raise ValueError("No API key configured for LLM")
    
    async def analyze_cv(self, cv_content: str, job_description: str = "") -> CVAnalysis:
        """Analyze CV content for completeness and optimization"""
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert CV analyst and career counselor. 
            Analyze the provided CV content and provide detailed feedback."""),
            HumanMessage(content=f"""
            Analyze this CV content:
            {cv_content}
            
            Job Description (if provided): {job_description}
            
            Provide analysis in the following format:
            {self.cv_analysis_parser.get_format_instructions()}
            """)
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(cv_content=cv_content, job_description=job_description)
        
        return self.cv_analysis_parser.parse(result)
    
    async def match_job_to_profile(self, profile_data: str, job_description: str) -> JobMatch:
        """Match job requirements to user profile"""
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert recruiter and job matching specialist. 
            Analyze how well a candidate profile matches a job description."""),
            HumanMessage(content=f"""
            Candidate Profile:
            {profile_data}
            
            Job Description:
            {job_description}
            
            Analyze the match and provide results in this format:
            {self.job_match_parser.get_format_instructions()}
            """)
        ])
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = await chain.arun(profile_data=profile_data, job_description=job_description)
        
        return self.job_match_parser.parse(result)
    
    async def generate_tailored_cv(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a tailored CV for a specific job"""
        
        # Step 1: Analyze job requirements
        job_analysis_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a job market analyst. Extract key requirements from job descriptions."),
            HumanMessage(content=f"""
            Analyze this job posting and identify:
            1. Required skills and technologies
            2. Experience level needed
            3. Key responsibilities
            4. Company culture indicators
            5. ATS keywords to include
            
            Job Title: {job.title}
            Company: {job.company}
            Description: {job.description}
            Requirements: {job.requirements}
            """)
        ])
        
        job_chain = LLMChain(llm=self.llm, prompt=job_analysis_prompt)
        job_analysis = await job_chain.arun(
            title=job.title,
            company=job.company,
            description=job.description,
            requirements=job.requirements
        )
        
        # Step 2: Generate tailored CV
        cv_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert CV writer. Create professional, 
            ATS-optimized CVs that highlight relevant experience for specific roles."""),
            HumanMessage(content=f"""
            Create a tailored CV for this candidate applying to the analyzed job.
            
            Job Analysis:
            {job_analysis}
            
            Candidate Information:
            Name: {profile.personal_info.full_name}
            Email: {profile.personal_info.email}
            Phone: {profile.personal_info.phone}
            Location: {profile.personal_info.location}
            
            Experience: {[exp.dict() for exp in profile.experience]}
            Education: {[edu.dict() for edu in profile.education]}
            Skills: {profile.skills}
            
            Create a professional CV that:
            1. Highlights most relevant experience first
            2. Uses keywords from the job description
            3. Is ATS-friendly
            4. Shows quantifiable achievements
            5. Matches the job requirements
            """)
        ])
        
        cv_chain = LLMChain(llm=self.llm, prompt=cv_prompt)
        cv_content = await cv_chain.arun(
            job_analysis=job_analysis,
            profile=profile.dict()
        )
        
        return {
            "cv_content": cv_content,
            "job_analysis": job_analysis,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_cover_letter(self, profile: CompleteProfile, job: Job) -> Dict[str, Any]:
        """Generate a personalized cover letter"""
        
        # Step 1: Research company and role
        research_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a company researcher. Analyze companies and roles for cover letter writing."),
            HumanMessage(content=f"""
            Research insights for cover letter writing:
            
            Company: {job.company}
            Job Title: {job.title}
            Job Description: {job.description}
            
            Identify:
            1. Company values and culture
            2. What they're looking for in candidates
            3. Key selling points to emphasize
            4. Tone and style to use
            """)
        ])
        
        research_chain = LLMChain(llm=self.llm, prompt=research_prompt)
        company_research = await research_chain.arun(
            company=job.company,
            title=job.title,
            description=job.description
        )
        
        # Step 2: Write cover letter
        cover_letter_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a professional cover letter writer. 
            Write compelling, personalized cover letters that get interviews."""),
            HumanMessage(content=f"""
            Write a cover letter for this application:
            
            Company Research:
            {company_research}
            
            Candidate Profile:
            Name: {profile.personal_info.full_name}
            Experience: {[exp.dict() for exp in profile.experience]}
            Skills: {profile.skills}
            
            Job: {job.title} at {job.company}
            
            Write a cover letter that:
            1. Shows genuine interest in the company
            2. Highlights most relevant experience
            3. Demonstrates cultural fit
            4. Is concise but impactful (max 400 words)
            5. Has a strong opening and closing
            """)
        ])
        
        cover_letter_chain = LLMChain(llm=self.llm, prompt=cover_letter_prompt)
        cover_letter = await cover_letter_chain.arun(
            research=company_research,
            profile=profile.dict(),
            job=job.dict()
        )
        
        return {
            "cover_letter": cover_letter,
            "company_research": company_research,
            "generated_at": datetime.utcnow().isoformat()
        }


# Global service instance
langchain_ai_service = LangChainAIService()
