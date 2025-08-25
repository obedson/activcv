"""
Advanced job description analysis and CV tailoring service
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from app.services.crew_agents import crew_service
from app.models.profile import CompleteProfile
from app.models.jobs import Job

logger = logging.getLogger(__name__)


class RequirementType(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    PREFERRED = "preferred"


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class ExtractedRequirement:
    """Extracted job requirement"""
    text: str
    type: RequirementType
    category: str  # technical, soft_skill, experience, education, etc.
    importance_score: float  # 0-1
    keywords: List[str]


@dataclass
class SkillMatch:
    """Skill matching result"""
    skill: str
    required_level: Optional[SkillLevel]
    user_level: Optional[SkillLevel]
    match_score: float  # 0-1
    evidence: List[str]  # Evidence from user profile


@dataclass
class TailoringRecommendation:
    """CV tailoring recommendation"""
    section: str  # summary, experience, skills, etc.
    action: str  # emphasize, add, modify, reorder
    content: str
    reason: str
    priority: int  # 1-5, 1 being highest


class JobDescriptionAnalyzer:
    """Advanced job description analysis and CV tailoring"""
    
    def __init__(self):
        self.technical_skills_patterns = self._load_technical_patterns()
        self.soft_skills_patterns = self._load_soft_skills_patterns()
        self.requirement_indicators = self._load_requirement_indicators()
        self.experience_patterns = self._load_experience_patterns()
    
    def _load_technical_patterns(self) -> Dict[str, List[str]]:
        """Load technical skill patterns"""
        return {
            "programming_languages": [
                r"\b(python|java|javascript|typescript|c\+\+|c#|php|ruby|go|rust|swift|kotlin)\b",
                r"\b(html|css|sql|r|matlab|scala|perl|shell|bash)\b"
            ],
            "frameworks": [
                r"\b(react|angular|vue|django|flask|spring|express|laravel|rails)\b",
                r"\b(tensorflow|pytorch|scikit-learn|pandas|numpy)\b"
            ],
            "databases": [
                r"\b(mysql|postgresql|mongodb|redis|elasticsearch|oracle|sqlite)\b",
                r"\b(dynamodb|cassandra|neo4j|influxdb)\b"
            ],
            "cloud_platforms": [
                r"\b(aws|azure|gcp|google cloud|amazon web services)\b",
                r"\b(docker|kubernetes|terraform|ansible)\b"
            ],
            "tools": [
                r"\b(git|jenkins|jira|confluence|slack|figma|sketch)\b",
                r"\b(tableau|power bi|excel|photoshop|illustrator)\b"
            ]
        }
    
    def _load_soft_skills_patterns(self) -> List[str]:
        """Load soft skill patterns"""
        return [
            r"\b(leadership|communication|teamwork|collaboration)\b",
            r"\b(problem.solving|analytical|critical.thinking)\b",
            r"\b(adaptability|flexibility|creativity|innovation)\b",
            r"\b(time.management|organization|attention.to.detail)\b",
            r"\b(customer.service|client.facing|stakeholder.management)\b"
        ]
    
    def _load_requirement_indicators(self) -> Dict[RequirementType, List[str]]:
        """Load requirement type indicators"""
        return {
            RequirementType.MUST_HAVE: [
                r"\brequired?\b", r"\bmust\s+have\b", r"\bessential\b",
                r"\bmandatory\b", r"\bnecessary\b", r"\bneeded\b"
            ],
            RequirementType.NICE_TO_HAVE: [
                r"\bnice\s+to\s+have\b", r"\bbonus\b", r"\bplus\b",
                r"\badditional\b", r"\boptional\b"
            ],
            RequirementType.PREFERRED: [
                r"\bpreferred\b", r"\bdesired\b", r"\bideal\b",
                r"\bwould\s+be\s+great\b", r"\ba\s+plus\b"
            ]
        }
    
    def _load_experience_patterns(self) -> List[str]:
        """Load experience level patterns"""
        return [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"(\d+)\+?\s*years?\s+(?:in|with|using)",
            r"(junior|senior|lead|principal|staff|entry.level)",
            r"(beginner|intermediate|advanced|expert|proficient)"
        ]
    
    async def analyze_job_description(self, job: Job) -> Dict[str, Any]:
        """Comprehensive job description analysis"""
        try:
            job_text = f"{job.title} {job.description} {job.requirements or ''}"
            
            # Extract requirements
            requirements = self._extract_requirements(job_text)
            
            # Extract skills
            technical_skills = self._extract_technical_skills(job_text)
            soft_skills = self._extract_soft_skills(job_text)
            
            # Extract experience requirements
            experience_requirements = self._extract_experience_requirements(job_text)
            
            # Extract education requirements
            education_requirements = self._extract_education_requirements(job_text)
            
            # Analyze company culture indicators
            culture_indicators = self._analyze_company_culture(job_text)
            
            # Extract keywords for ATS optimization
            ats_keywords = self._extract_ats_keywords(job_text)
            
            # Use AI for deeper analysis
            ai_analysis = await self._ai_enhanced_analysis(job)
            
            return {
                "job_id": job.id,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "requirements": {
                    "must_have": [r for r in requirements if r.type == RequirementType.MUST_HAVE],
                    "nice_to_have": [r for r in requirements if r.type == RequirementType.NICE_TO_HAVE],
                    "preferred": [r for r in requirements if r.type == RequirementType.PREFERRED]
                },
                "skills": {
                    "technical": technical_skills,
                    "soft": soft_skills
                },
                "experience": experience_requirements,
                "education": education_requirements,
                "culture": culture_indicators,
                "ats_keywords": ats_keywords,
                "ai_insights": ai_analysis,
                "complexity_score": self._calculate_complexity_score(requirements, technical_skills),
                "match_difficulty": self._assess_match_difficulty(requirements)
            }
            
        except Exception as e:
            logger.error(f"Job description analysis failed: {e}")
            return {"error": str(e), "job_id": job.id}
    
    def _extract_requirements(self, job_text: str) -> List[ExtractedRequirement]:
        """Extract structured requirements from job text"""
        requirements = []
        sentences = re.split(r'[.!?]+', job_text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
            
            # Determine requirement type
            req_type = RequirementType.NICE_TO_HAVE  # default
            for rtype, patterns in self.requirement_indicators.items():
                if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in patterns):
                    req_type = rtype
                    break
            
            # Categorize requirement
            category = self._categorize_requirement(sentence)
            
            # Calculate importance score
            importance = self._calculate_importance_score(sentence, req_type)
            
            # Extract keywords
            keywords = self._extract_keywords_from_sentence(sentence)
            
            if keywords:  # Only add if we found relevant keywords
                requirements.append(ExtractedRequirement(
                    text=sentence,
                    type=req_type,
                    category=category,
                    importance_score=importance,
                    keywords=keywords
                ))
        
        return requirements
    
    def _extract_technical_skills(self, job_text: str) -> Dict[str, List[str]]:
        """Extract technical skills by category"""
        skills = {}
        
        for category, patterns in self.technical_skills_patterns.items():
            found_skills = set()
            for pattern in patterns:
                matches = re.findall(pattern, job_text, re.IGNORECASE)
                found_skills.update(matches)
            
            if found_skills:
                skills[category] = list(found_skills)
        
        return skills
    
    def _extract_soft_skills(self, job_text: str) -> List[str]:
        """Extract soft skills"""
        soft_skills = set()
        
        for pattern in self.soft_skills_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE)
            soft_skills.update(matches)
        
        return list(soft_skills)
    
    def _extract_experience_requirements(self, job_text: str) -> Dict[str, Any]:
        """Extract experience requirements"""
        experience = {
            "years_required": None,
            "level": None,
            "specific_experience": []
        }
        
        # Extract years of experience
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    # Years pattern
                    try:
                        years = int(matches[0][0]) if matches[0][0].isdigit() else None
                        if years:
                            experience["years_required"] = years
                    except (ValueError, IndexError):
                        pass
                else:
                    # Level pattern
                    level = matches[0].lower().replace('.', ' ')
                    experience["level"] = level
        
        return experience
    
    def _extract_education_requirements(self, job_text: str) -> Dict[str, Any]:
        """Extract education requirements"""
        education_patterns = [
            r"\b(bachelor'?s?|ba|bs|undergraduate)\b",
            r"\b(master'?s?|ma|ms|mba|graduate)\b",
            r"\b(phd|doctorate|doctoral)\b",
            r"\b(degree|diploma|certification)\b"
        ]
        
        education = {
            "degree_required": False,
            "degree_level": None,
            "field_of_study": [],
            "certifications": []
        }
        
        for pattern in education_patterns:
            if re.search(pattern, job_text, re.IGNORECASE):
                education["degree_required"] = True
                matches = re.findall(pattern, job_text, re.IGNORECASE)
                if matches:
                    education["degree_level"] = matches[0].lower()
                break
        
        return education
    
    def _analyze_company_culture(self, job_text: str) -> Dict[str, Any]:
        """Analyze company culture indicators"""
        culture_keywords = {
            "collaborative": ["team", "collaborate", "together", "partnership"],
            "innovative": ["innovation", "creative", "cutting-edge", "pioneering"],
            "fast_paced": ["fast-paced", "dynamic", "agile", "rapid"],
            "growth_oriented": ["growth", "scale", "expand", "opportunity"],
            "remote_friendly": ["remote", "flexible", "work from home", "distributed"]
        }
        
        culture_scores = {}
        for trait, keywords in culture_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in job_text.lower())
            culture_scores[trait] = score / len(keywords)  # Normalize
        
        return culture_scores
    
    def _extract_ats_keywords(self, job_text: str) -> List[str]:
        """Extract keywords for ATS optimization"""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        # Extract words and phrases
        words = re.findall(r'\b[a-zA-Z]{3,}\b', job_text.lower())
        phrases = re.findall(r'\b[a-zA-Z]+(?:\s+[a-zA-Z]+){1,2}\b', job_text.lower())
        
        # Filter and score keywords
        keywords = []
        word_freq = {}
        
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and take top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_keywords[:50] if freq > 1]
        
        return keywords
    
    async def _ai_enhanced_analysis(self, job: Job) -> Dict[str, Any]:
        """Use AI for enhanced job analysis"""
        try:
            # Use CrewAI for deeper analysis
            analysis_result = await crew_service.analyze_job_match(
                user_profile=None,  # We'll analyze without user profile first
                job=job
            )
            
            return {
                "ai_extracted_skills": analysis_result.get("skills", []),
                "ai_requirements": analysis_result.get("requirements", []),
                "ai_insights": analysis_result.get("insights", ""),
                "complexity_assessment": analysis_result.get("complexity", "medium")
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"error": "AI analysis unavailable"}
    
    def _categorize_requirement(self, sentence: str) -> str:
        """Categorize a requirement sentence"""
        categories = {
            "technical": ["programming", "software", "system", "database", "api", "framework"],
            "experience": ["experience", "years", "worked", "background"],
            "education": ["degree", "bachelor", "master", "phd", "education", "university"],
            "soft_skill": ["communication", "leadership", "team", "management", "interpersonal"],
            "domain": ["industry", "domain", "sector", "field", "business"]
        }
        
        sentence_lower = sentence.lower()
        for category, keywords in categories.items():
            if any(keyword in sentence_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _calculate_importance_score(self, sentence: str, req_type: RequirementType) -> float:
        """Calculate importance score for a requirement"""
        base_score = {
            RequirementType.MUST_HAVE: 1.0,
            RequirementType.PREFERRED: 0.7,
            RequirementType.NICE_TO_HAVE: 0.4
        }[req_type]
        
        # Adjust based on emphasis words
        emphasis_words = ["critical", "essential", "key", "important", "vital"]
        emphasis_bonus = sum(0.1 for word in emphasis_words if word in sentence.lower())
        
        return min(1.0, base_score + emphasis_bonus)
    
    def _extract_keywords_from_sentence(self, sentence: str) -> List[str]:
        """Extract relevant keywords from a sentence"""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        
        # Filter for relevant technical and professional terms
        relevant_words = []
        for word in words:
            if (len(word) > 3 and 
                not word in ['with', 'have', 'will', 'must', 'should', 'would', 'could']):
                relevant_words.append(word)
        
        return relevant_words[:5]  # Limit to top 5 keywords per sentence
    
    def _calculate_complexity_score(self, requirements: List[ExtractedRequirement], 
                                  technical_skills: Dict[str, List[str]]) -> float:
        """Calculate job complexity score"""
        # Base complexity from number of requirements
        req_complexity = len(requirements) / 20.0  # Normalize to 0-1
        
        # Technical complexity from number of technical skills
        tech_count = sum(len(skills) for skills in technical_skills.values())
        tech_complexity = tech_count / 15.0  # Normalize to 0-1
        
        # Must-have requirements add complexity
        must_have_count = sum(1 for req in requirements if req.type == RequirementType.MUST_HAVE)
        must_have_complexity = must_have_count / 10.0  # Normalize to 0-1
        
        # Combine scores
        total_complexity = (req_complexity + tech_complexity + must_have_complexity) / 3
        return min(1.0, total_complexity)
    
    def _assess_match_difficulty(self, requirements: List[ExtractedRequirement]) -> str:
        """Assess how difficult it would be to match this job"""
        must_have_count = sum(1 for req in requirements if req.type == RequirementType.MUST_HAVE)
        high_importance_count = sum(1 for req in requirements if req.importance_score > 0.8)
        
        if must_have_count > 8 or high_importance_count > 10:
            return "high"
        elif must_have_count > 4 or high_importance_count > 5:
            return "medium"
        else:
            return "low"
    
    async def generate_tailoring_recommendations(
        self, 
        job_analysis: Dict[str, Any], 
        user_profile: CompleteProfile
    ) -> List[TailoringRecommendation]:
        """Generate CV tailoring recommendations based on job analysis"""
        try:
            recommendations = []
            
            # Analyze skill gaps
            skill_gaps = self._analyze_skill_gaps(job_analysis, user_profile)
            
            # Generate recommendations for each section
            recommendations.extend(self._recommend_summary_changes(job_analysis, user_profile))
            recommendations.extend(self._recommend_experience_changes(job_analysis, user_profile))
            recommendations.extend(self._recommend_skills_changes(job_analysis, user_profile, skill_gaps))
            recommendations.extend(self._recommend_keyword_optimization(job_analysis, user_profile))
            
            # Sort by priority
            recommendations.sort(key=lambda x: x.priority)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate tailoring recommendations: {e}")
            return []
    
    def _analyze_skill_gaps(self, job_analysis: Dict[str, Any], 
                          user_profile: CompleteProfile) -> List[str]:
        """Analyze skill gaps between job requirements and user profile"""
        required_skills = set()
        
        # Extract required technical skills
        for category, skills in job_analysis.get("skills", {}).get("technical", {}).items():
            required_skills.update(skill.lower() for skill in skills)
        
        # Extract user skills
        user_skills = set()
        if user_profile.skills:
            user_skills.update(skill.skill_name.lower() for skill in user_profile.skills)
        
        # Find gaps
        skill_gaps = list(required_skills - user_skills)
        return skill_gaps[:10]  # Limit to top 10 gaps
    
    def _recommend_summary_changes(self, job_analysis: Dict[str, Any], 
                                 user_profile: CompleteProfile) -> List[TailoringRecommendation]:
        """Recommend changes to professional summary"""
        recommendations = []
        
        # Extract key job keywords for summary
        ats_keywords = job_analysis.get("ats_keywords", [])[:5]
        
        if ats_keywords:
            recommendations.append(TailoringRecommendation(
                section="summary",
                action="modify",
                content=f"Incorporate these key terms: {', '.join(ats_keywords)}",
                reason="Improve ATS compatibility and keyword matching",
                priority=1
            ))
        
        return recommendations
    
    def _recommend_experience_changes(self, job_analysis: Dict[str, Any], 
                                    user_profile: CompleteProfile) -> List[TailoringRecommendation]:
        """Recommend changes to experience section"""
        recommendations = []
        
        # Recommend emphasizing relevant experience
        must_have_reqs = job_analysis.get("requirements", {}).get("must_have", [])
        
        if must_have_reqs:
            recommendations.append(TailoringRecommendation(
                section="experience",
                action="emphasize",
                content="Highlight experience that matches must-have requirements",
                reason="Align experience with critical job requirements",
                priority=2
            ))
        
        return recommendations
    
    def _recommend_skills_changes(self, job_analysis: Dict[str, Any], 
                                user_profile: CompleteProfile, 
                                skill_gaps: List[str]) -> List[TailoringRecommendation]:
        """Recommend changes to skills section"""
        recommendations = []
        
        # Recommend adding missing skills if user has them
        if skill_gaps:
            recommendations.append(TailoringRecommendation(
                section="skills",
                action="add",
                content=f"Consider adding these relevant skills if you have them: {', '.join(skill_gaps[:5])}",
                reason="Address skill gaps identified in job requirements",
                priority=3
            ))
        
        return recommendations
    
    def _recommend_keyword_optimization(self, job_analysis: Dict[str, Any], 
                                      user_profile: CompleteProfile) -> List[TailoringRecommendation]:
        """Recommend keyword optimization"""
        recommendations = []
        
        ats_keywords = job_analysis.get("ats_keywords", [])
        
        if ats_keywords:
            recommendations.append(TailoringRecommendation(
                section="overall",
                action="optimize",
                content=f"Ensure these keywords appear naturally throughout your CV: {', '.join(ats_keywords[:10])}",
                reason="Optimize for ATS scanning and keyword matching",
                priority=4
            ))
        
        return recommendations


# Global service instance
job_description_analyzer = JobDescriptionAnalyzer()