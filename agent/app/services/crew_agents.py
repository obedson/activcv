"""
CrewAI agents for intelligent CV processing and generation
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_openai import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

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
        return list(cv_words.intersection(job_words))
    
    def _generate_suggestions(self, content: str) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        if len(content) < 500:
            suggestions.append("Consider adding more detailed descriptions of your experience")
        if "achievement" not in content.lower():
            suggestions.append("Include quantifiable achievements and results")
        if not any(skill in content.lower() for skill in ["python", "javascript", "java", "react"]):
            suggestions.append("Consider highlighting technical skills more prominently")
        return suggestions
    
    def _check_ats_compatibility(self, content: str) -> Dict[str, bool]:
        """Check ATS compatibility factors"""
        return {
            "has_clear_sections": any(header in content for header in ["EXPERIENCE", "EDUCATION", "SKILLS"]),
            "uses_standard_fonts": True,  # Assume true for text content
            "has_contact_info": "@" in content,  # Simple email check
            "reasonable_length": 500 <= len(content) <= 3000
        }


class JobMatchingTool(BaseTool):
    """Tool for matching jobs to user profiles"""
    name: str = "job_matching_tool"
    description: str = "Matches job requirements with user profile and calculates compatibility scores"

    def _run(self, user_profile: str, job_description: str) -> str:
        """Calculate job match score and provide reasoning"""
        match_data = {
            "overall_score": self._calculate_match_score(user_profile, job_description),
            "skill_matches": self._match_skills(user_profile, job_description),
            "experience_relevance": self._assess_experience(user_profile, job_description),
            "recommendations": self._generate_recommendations(user_profile, job_description)
        }
        return str(match_data)
    
    def _calculate_match_score(self, profile: str, job_desc: str) -> float:
        """Calculate overall match score"""
        profile_words = set(profile.lower().split())
        job_words = set(job_desc.lower().split())
        
        if not job_words:
            return 0.0
        
        matches = len(profile_words.intersection(job_words))
        return min(matches / len(job_words) * 2, 1.0)  # Cap at 1.0
    
    def _match_skills(self, profile: str, job_desc: str) -> List[str]:
        """Find matching skills"""
        common_skills = ["python", "javascript", "react", "node", "sql", "aws", "docker", "git"]
        profile_lower = profile.lower()
        job_lower = job_desc.lower()
        
        return [skill for skill in common_skills if skill in profile_lower and skill in job_lower]
    
    def _assess_experience(self, profile: str, job_desc: str) -> str:
        """Assess experience relevance"""
        if "senior" in job_desc.lower() and "senior" in profile.lower():
            return "Strong match - Senior level experience"
        elif "junior" in job_desc.lower() or "entry" in job_desc.lower():
            return "Good match - Entry to mid-level position"
        else:
            return "Moderate match - Review experience requirements"
    
    def _generate_recommendations(self, profile: str, job_desc: str) -> List[str]:
        """Generate application recommendations"""
        recommendations = []
        
        if "remote" in job_desc.lower():
            recommendations.append("Highlight remote work experience and self-management skills")
        
        if any(tech in job_desc.lower() for tech in ["python", "javascript", "react"]):
            recommendations.append("Emphasize technical projects and coding experience")
        
        if "leadership" in job_desc.lower():
            recommendations.append("Showcase leadership experience and team management skills")
        
        return recommendations


class CrewAIService:
    """Service for managing CrewAI agents and tasks"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = [CVAnalysisTool(), JobMatchingTool()]
        self.agents = self._create_agents()
    
    def _initialize_llm(self):
        """Initialize the language model"""
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
            # Fallback to a mock LLM for development
            return self._create_mock_llm()
    
    def _create_mock_llm(self):
        """Create a mock LLM for development/testing"""
        class MockLLM:
            def __call__(self, prompt: str) -> str:
                return f"Mock response for: {prompt[:100]}..."
            
            def invoke(self, prompt: str) -> str:
                return self.__call__(prompt)
        
        return MockLLM()
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create specialized AI agents"""
        
        # Intake Agent - Processes user input and requirements
        intake_agent = Agent(
            role="CV Intake Specialist",
            goal="Understand user requirements and gather comprehensive profile information",
            backstory="""You are an expert CV consultant who specializes in understanding 
            job seekers' needs and extracting comprehensive professional information. You excel 
            at asking the right questions and organizing information effectively.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Parse Agent - Extracts and structures data from CVs
        parse_agent = Agent(
            role="CV Parser and Data Extractor",
            goal="Extract structured information from CV documents and text",
            backstory="""You are a meticulous data extraction specialist who can parse 
            any CV format and extract structured professional information. You understand 
            various CV formats and can identify key information accurately.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Schema Agent - Normalizes and validates data
        schema_agent = Agent(
            role="Data Schema Validator",
            goal="Normalize and validate extracted CV data according to standard schemas",
            backstory="""You are a data quality expert who ensures all extracted 
            information follows proper schemas and formats. You validate data integrity 
            and consistency across different sources.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # JD Analysis Agent - Analyzes job descriptions
        jd_analysis_agent = Agent(
            role="Job Description Analyst",
            goal="Analyze job descriptions and extract key requirements and keywords",
            backstory="""You are an expert recruiter who understands job requirements 
            deeply. You can identify key skills, experience levels, and cultural fit 
            indicators from job descriptions.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Tailor Agent - Customizes CVs for specific jobs
        tailor_agent = Agent(
            role="CV Tailoring Specialist",
            goal="Customize CV content to match specific job requirements while maintaining truthfulness",
            backstory="""You are a professional CV writer who specializes in tailoring 
            resumes for specific positions. You know how to highlight relevant experience 
            and skills while maintaining complete honesty and accuracy.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Stylist Agent - Applies formatting and templates
        stylist_agent = Agent(
            role="CV Design and Formatting Expert",
            goal="Apply professional formatting and design to CV content",
            backstory="""You are a professional document designer who creates visually 
            appealing and ATS-friendly CV layouts. You understand modern design principles 
            and recruitment system requirements.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # QA Agent - Reviews and validates final output
        qa_agent = Agent(
            role="Quality Assurance Specialist",
            goal="Review and validate CV quality, accuracy, and effectiveness",
            backstory="""You are a meticulous quality assurance expert who ensures 
            every CV meets the highest standards. You check for accuracy, consistency, 
            formatting, and overall effectiveness.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Delivery Agent - Handles final delivery and notifications
        delivery_agent = Agent(
            role="CV Delivery Coordinator",
            goal="Handle final CV delivery and user notifications",
            backstory="""You are a customer service expert who ensures smooth delivery 
            of completed CVs. You handle notifications, follow-ups, and user communication 
            with professionalism and care.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Cover Letter Writer Agent - Specializes in cover letter creation
        cover_letter_writer = Agent(
            role="Professional Cover Letter Writer",
            goal="Create compelling, personalized cover letters that highlight relevant qualifications",
            backstory="""You are an expert cover letter writer with years of experience 
            helping job seekers land interviews. You know how to craft compelling narratives 
            that connect a candidate's experience to specific job requirements while 
            maintaining authenticity and professional tone.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Company Research Agent - Researches companies for personalization
        company_research_agent = Agent(
            role="Company Research Specialist",
            goal="Research companies to provide insights for personalized cover letters",
            backstory="""You are a research expert who specializes in gathering company 
            information, culture insights, and recent developments to help personalize 
            job applications. You understand how to find relevant details that make 
            cover letters stand out.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        return {
            "intake": intake_agent,
            "parse": parse_agent,
            "schema": schema_agent,
            "jd_analysis": jd_analysis_agent,
            "tailor": tailor_agent,
            "stylist": stylist_agent,
            "qa": qa_agent,
            "delivery": delivery_agent,
            "cover_letter_writer": cover_letter_writer,
            "company_research": company_research_agent
        }
    
    async def process_cv_generation(
        self, 
        user_profile: CompleteProfile, 
        job: Optional[Job] = None,
        template: str = "modern_one_page"
    ) -> Dict[str, Any]:
        """Process complete CV generation workflow"""
        
        # Create tasks for the workflow
        tasks = []
        
        # Task 1: Analyze user profile
        profile_analysis_task = Task(
            description=f"""Analyze the user profile for completeness and quality:
            Profile Data: {user_profile.dict()}
            
            Assess:
            1. Profile completeness
            2. Content quality
            3. Missing information
            4. Improvement opportunities
            """,
            agent=self.agents["intake"],
            expected_output="Detailed profile analysis with completeness score and recommendations"
        )
        tasks.append(profile_analysis_task)
        
        # Task 2: Job analysis (if job provided)
        if job:
            job_analysis_task = Task(
                description=f"""Analyze the job description and requirements:
                Job Title: {job.title}
                Company: {job.company}
                Description: {job.description}
                Requirements: {job.requirements}
                
                Extract:
                1. Key requirements
                2. Required skills
                3. Experience level
                4. Cultural indicators
                """,
                agent=self.agents["jd_analysis"],
                expected_output="Structured job analysis with key requirements and matching criteria"
            )
            tasks.append(job_analysis_task)
        
        # Task 3: CV tailoring
        tailoring_task = Task(
            description=f"""Create tailored CV content based on profile and job requirements:
            User Profile: {user_profile.dict()}
            Job Requirements: {job.dict() if job else 'General CV'}
            Template: {template}
            
            Generate:
            1. Tailored professional summary
            2. Optimized experience descriptions
            3. Relevant skills highlighting
            4. Achievement emphasis
            """,
            agent=self.agents["tailor"],
            expected_output="Tailored CV content optimized for the target position"
        )
        tasks.append(tailoring_task)
        
        # Task 4: Quality assurance
        qa_task = Task(
            description="""Review the generated CV content for:
            1. Accuracy and truthfulness
            2. Grammar and spelling
            3. Consistency and flow
            4. ATS compatibility
            5. Professional presentation
            """,
            agent=self.agents["qa"],
            expected_output="Quality assessment report with final CV recommendations"
        )
        tasks.append(qa_task)
        
        # Create and execute crew
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            
            return {
                "success": True,
                "result": result,
                "generated_content": self._extract_cv_content(result),
                "metadata": {
                    "template": template,
                    "job_id": job.id if job else None,
                    "generated_at": datetime.utcnow().isoformat(),
                    "agents_used": list(self.agents.keys())
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "template": template,
                    "job_id": job.id if job else None,
                    "failed_at": datetime.utcnow().isoformat()
                }
            }
    
    def _extract_cv_content(self, crew_result: str) -> Dict[str, str]:
        """Extract structured CV content from crew result"""
        # This would parse the crew result and extract structured content
        # For now, return a basic structure
        return {
            "summary": "AI-generated professional summary based on profile analysis",
            "experience": "Tailored experience descriptions highlighting relevant achievements",
            "skills": "Optimized skills section matching job requirements",
            "education": "Education section with relevant coursework and achievements",
            "raw_output": str(crew_result)
        }
    
    async def analyze_job_match(
        self, 
        user_profile: CompleteProfile, 
        job: Job
    ) -> Dict[str, Any]:
        """Analyze job match using AI agents"""
        
        match_task = Task(
            description=f"""Analyze job compatibility:
            User Profile: {user_profile.dict()}
            Job: {job.dict()}
            
            Provide:
            1. Overall match score (0-1)
            2. Skill alignment analysis
            3. Experience relevance assessment
            4. Application recommendations
            5. Areas for improvement
            """,
            agent=self.agents["jd_analysis"],
            expected_output="Comprehensive job match analysis with actionable recommendations"
        )
        
        crew = Crew(
            agents=[self.agents["jd_analysis"]],
            tasks=[match_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            return {
                "success": True,
                "analysis": str(result),
                "match_score": self._extract_match_score(result),
                "recommendations": self._extract_recommendations(result)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_match_score(self, result: str) -> float:
        """Extract match score from analysis result"""
        # Simple extraction - in production, this would be more sophisticated
        if "high match" in result.lower():
            return 0.8
        elif "good match" in result.lower():
            return 0.6
        elif "moderate match" in result.lower():
            return 0.4
        else:
            return 0.2
    
    def _extract_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from analysis result"""
        # Simple extraction - in production, this would parse structured output
        recommendations = []
        if "highlight" in result.lower():
            recommendations.append("Highlight relevant experience and skills")
        if "emphasize" in result.lower():
            recommendations.append("Emphasize matching qualifications")
        if "improve" in result.lower():
            recommendations.append("Consider improving weak areas")
        
        return recommendations if recommendations else ["Review job requirements and tailor application accordingly"]
    
    async def generate_cover_letter(
        self,
        user_profile: CompleteProfile,
        job: Job,
        template_style: str = "professional",
        customizations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a personalized cover letter using AI agents"""
        
        customizations = customizations or {}
        
        # Create tasks for cover letter generation
        tasks = []
        
        # Task 1: Company research
        company_research_task = Task(
            description=f"""Research the company and role for personalization:
            Company: {job.company}
            Job Title: {job.title}
            Job Description: {job.description}
            
            Research and provide:
            1. Company mission and values
            2. Recent company news or developments
            3. Company culture insights
            4. Industry context and trends
            5. Specific role requirements and expectations
            """,
            agent=self.agents["company_research"],
            expected_output="Comprehensive company research with personalization insights"
        )
        tasks.append(company_research_task)
        
        # Task 2: Profile analysis for cover letter
        profile_analysis_task = Task(
            description=f"""Analyze user profile for cover letter content:
            User Profile: {user_profile.dict()}
            Target Job: {job.title} at {job.company}
            
            Identify:
            1. Most relevant experiences for this role
            2. Key achievements that align with job requirements
            3. Skills that match job needs
            4. Unique value proposition
            5. Career narrative that connects to this opportunity
            """,
            agent=self.agents["intake"],
            expected_output="Profile analysis highlighting most relevant qualifications for the cover letter"
        )
        tasks.append(profile_analysis_task)
        
        # Task 3: Cover letter writing
        cover_letter_writing_task = Task(
            description=f"""Write a compelling cover letter:
            User Profile Analysis: [Previous task output]
            Company Research: [Previous task output]
            Job Details: {job.dict()}
            Template Style: {template_style}
            Customizations: {customizations}
            
            Create a cover letter with:
            1. Engaging opening that shows genuine interest
            2. Body paragraphs highlighting relevant experience and achievements
            3. Specific examples that demonstrate value to the company
            4. Knowledge of company/role showing research and genuine interest
            5. Strong closing with clear call to action
            6. Professional tone matching the {template_style} style
            
            Requirements:
            - Keep to 3-4 paragraphs maximum
            - Use specific examples and quantifiable achievements
            - Show enthusiasm and cultural fit
            - Maintain professional yet personable tone
            - Include company-specific details from research
            """,
            agent=self.agents["cover_letter_writer"],
            expected_output="Complete, compelling cover letter tailored to the specific job and company"
        )
        tasks.append(cover_letter_writing_task)
        
        # Task 4: Quality review for cover letter
        cover_letter_qa_task = Task(
            description="""Review the cover letter for:
            1. Grammar, spelling, and punctuation
            2. Professional tone and appropriate language
            3. Logical flow and structure
            4. Relevance to job requirements
            5. Personalization and company-specific details
            6. Call to action effectiveness
            7. Overall impact and persuasiveness
            8. Length appropriateness (not too long/short)
            """,
            agent=self.agents["qa"],
            expected_output="Quality-reviewed cover letter with any necessary improvements"
        )
        tasks.append(cover_letter_qa_task)
        
        # Create and execute crew
        crew = Crew(
            agents=[
                self.agents["company_research"],
                self.agents["intake"],
                self.agents["cover_letter_writer"],
                self.agents["qa"]
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            
            # Extract the final cover letter content
            cover_letter_content = self._extract_cover_letter_content(result)
            
            return {
                "success": True,
                "cover_letter_content": cover_letter_content,
                "metadata": {
                    "template_style": template_style,
                    "job_id": job.id,
                    "company": job.company,
                    "job_title": job.title,
                    "generated_at": datetime.utcnow().isoformat(),
                    "word_count": len(cover_letter_content.split()) if cover_letter_content else 0,
                    "customizations_applied": customizations
                },
                "raw_output": str(result)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "template_style": template_style,
                    "job_id": job.id,
                    "failed_at": datetime.utcnow().isoformat()
                }
            }
    
    def _extract_cover_letter_content(self, crew_result: str) -> str:
        """Extract the final cover letter content from crew result"""
        # Convert crew result to string if it's not already
        result_str = str(crew_result)
        
        # Look for the final cover letter in the result
        # This is a simple extraction - in production, you'd want more sophisticated parsing
        lines = result_str.split('\n')
        
        # Find lines that look like cover letter content
        cover_letter_lines = []
        in_cover_letter = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and agent headers
            if not line or line.startswith('[') or line.startswith('Agent:') or line.startswith('Task:'):
                continue
            
            # Look for cover letter start indicators
            if any(indicator in line.lower() for indicator in ['dear', 'to whom', 'hiring manager']):
                in_cover_letter = True
            
            # Look for cover letter end indicators
            if any(indicator in line.lower() for indicator in ['sincerely', 'best regards', 'yours truly']):
                cover_letter_lines.append(line)
                in_cover_letter = False
                break
            
            if in_cover_letter:
                cover_letter_lines.append(line)
        
        # If we didn't find a structured cover letter, return the last substantial output
        if not cover_letter_lines:
            # Get the last few substantial lines as fallback
            substantial_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 20]
            if substantial_lines:
                return '\n\n'.join(substantial_lines[-10:])  # Last 10 substantial lines
        
        return '\n\n'.join(cover_letter_lines) if cover_letter_lines else result_str
    
    async def analyze_cover_letter_effectiveness(
        self,
        cover_letter_content: str,
        job: Job,
        user_profile: CompleteProfile
    ) -> Dict[str, Any]:
        """Analyze cover letter effectiveness and provide improvement suggestions"""
        
        analysis_task = Task(
            description=f"""Analyze cover letter effectiveness:
            Cover Letter: {cover_letter_content}
            Job Requirements: {job.dict()}
            User Profile: {user_profile.dict()}
            
            Analyze:
            1. Relevance to job requirements
            2. Use of specific examples and achievements
            3. Company knowledge demonstration
            4. Professional tone and language
            5. Structure and flow
            6. Call to action effectiveness
            7. Overall persuasiveness
            
            Provide:
            - Effectiveness score (0-10)
            - Specific strengths
            - Areas for improvement
            - Actionable recommendations
            """,
            agent=self.agents["qa"],
            expected_output="Comprehensive cover letter effectiveness analysis with improvement recommendations"
        )
        
        crew = Crew(
            agents=[self.agents["qa"]],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            return {
                "success": True,
                "analysis": str(result),
                "effectiveness_score": self._extract_effectiveness_score(result),
                "recommendations": self._extract_cover_letter_recommendations(result)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_effectiveness_score(self, result: str) -> float:
        """Extract effectiveness score from analysis result"""
        result_lower = result.lower()
        if "excellent" in result_lower or "outstanding" in result_lower:
            return 9.0
        elif "very good" in result_lower or "strong" in result_lower:
            return 8.0
        elif "good" in result_lower:
            return 7.0
        elif "satisfactory" in result_lower or "adequate" in result_lower:
            return 6.0
        elif "needs improvement" in result_lower:
            return 5.0
        else:
            return 6.5  # Default moderate score
    
    def _extract_cover_letter_recommendations(self, result: str) -> List[str]:
        """Extract recommendations from cover letter analysis"""
        recommendations = []
        result_lower = result.lower()
        
        if "specific examples" in result_lower:
            recommendations.append("Add more specific examples and quantifiable achievements")
        if "company research" in result_lower:
            recommendations.append("Include more company-specific details to show research")
        if "call to action" in result_lower:
            recommendations.append("Strengthen the call to action in the closing")
        if "tone" in result_lower:
            recommendations.append("Adjust tone to better match company culture")
        if "length" in result_lower:
            recommendations.append("Optimize length for better readability")
        
        return recommendations if recommendations else ["Consider adding more personalization and specific examples"]


# Global service instance
crew_service = CrewAIService()