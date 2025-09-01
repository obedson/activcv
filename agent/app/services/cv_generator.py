"""
CV generation service with multiple templates and AI-powered content optimization
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import jinja2
from io import BytesIO
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    from app.services.pdf_generator_fallback import PDFGeneratorFallback

from app.models.profile import CompleteProfile
from app.models.jobs import Job, GeneratedCVCreate
from app.services.crew_agents import crew_service
from app.services.storage import StorageService
from app.core.config import settings


class CVTemplate:
    """CV template configuration"""
    
    def __init__(self, name: str, template_file: str, css_file: str, description: str):
        self.name = name
        self.template_file = template_file
        self.css_file = css_file
        self.description = description


class CVGeneratorService:
    """Service for generating professional CVs with multiple templates"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "cv"
        self.templates = self._load_templates()
        self.jinja_env = self._setup_jinja_environment()
    
    def _load_templates(self) -> Dict[str, CVTemplate]:
        """Load available CV templates"""
        return {
            "modern_one_page": CVTemplate(
                name="Modern One Page",
                template_file="modern_one_page.html",
                css_file="modern_one_page.css",
                description="Clean, modern single-page design perfect for most industries"
            ),
            "professional_two_column": CVTemplate(
                name="Professional Two Column",
                template_file="professional_two_column.html",
                css_file="professional_two_column.css",
                description="Professional two-column layout with sidebar for skills and contact info"
            ),
            "corporate_traditional": CVTemplate(
                name="Corporate Traditional",
                template_file="corporate_traditional.html",
                css_file="corporate_traditional.css",
                description="Traditional corporate format ideal for conservative industries"
            ),
            "creative_portfolio": CVTemplate(
                name="Creative Portfolio",
                template_file="creative_portfolio.html",
                css_file="creative_portfolio.css",
                description="Creative design with portfolio sections for designers and creatives"
            ),
            "academic_research": CVTemplate(
                name="Academic Research",
                template_file="academic_research.html",
                css_file="academic_research.css",
                description="Academic CV format with emphasis on publications and research"
            ),
            "ats_optimized": CVTemplate(
                name="ATS Optimized",
                template_file="ats_optimized.html",
                css_file="ats_optimized.css",
                description="Highly ATS-friendly format with clean structure and standard fonts"
            )
        }
    
    def _setup_jinja_environment(self) -> jinja2.Environment:
        """Setup Jinja2 template environment"""
        loader = jinja2.FileSystemLoader(str(self.templates_dir))
        env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        env.filters['format_date'] = self._format_date
        env.filters['format_phone'] = self._format_phone
        env.filters['format_url'] = self._format_url
        env.filters['highlight_keywords'] = self._highlight_keywords
        
        return env
    
    def _format_date(self, date_str: str) -> str:
        """Format date for CV display"""
        if not date_str:
            return ""
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime("%B %Y")
        except:
            return date_str
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for display"""
        if not phone:
            return ""
        # Simple formatting - can be enhanced
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone
    
    def _format_url(self, url: str) -> str:
        """Format URL for display"""
        if not url:
            return ""
        if not url.startswith(('http://', 'https://')):
            return f"https://{url}"
        return url
    
    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """Highlight keywords in text (for HTML output)"""
        if not text or not keywords:
            return text
        
        highlighted = text
        for keyword in keywords:
            highlighted = highlighted.replace(
                keyword, 
                f'<span class="keyword-highlight">{keyword}</span>'
            )
        return highlighted
    
    async def generate_cv(
        self,
        user_id: str,
        user_profile: CompleteProfile,
        template_key: str = "modern_one_page",
        job: Optional[Job] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a complete CV with AI optimization"""
        
        try:
            # Validate template
            if template_key not in self.templates:
                raise ValueError(f"Template '{template_key}' not found")
            
            template = self.templates[template_key]
            
            # Use CrewAI for content optimization
            crew_result = await crew_service.process_cv_generation(
                user_profile=user_profile,
                job=job,
                template=template_key
            )
            
            if not crew_result["success"]:
                raise Exception(f"AI processing failed: {crew_result.get('error')}")
            
            # Prepare template context
            context = self._prepare_template_context(
                user_profile=user_profile,
                job=job,
                crew_result=crew_result,
                customizations=customizations or {}
            )
            
            # Generate HTML
            html_content = self._render_template(template, context)
            
            # Generate PDF
            pdf_content = self._generate_pdf(html_content, template)
            
            # Save to storage
            storage_service = StorageService(None)  # Will be injected properly
            file_path, pdf_url = await self._save_cv_file(
                user_id=user_id,
                pdf_content=pdf_content,
                filename=f"cv_{template_key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            
            return {
                "success": True,
                "pdf_url": pdf_url,
                "file_path": file_path,
                "file_size": len(pdf_content),
                "template_used": template_key,
                "generation_metadata": {
                    "template": template_key,
                    "job_tailored": job is not None,
                    "job_id": job.id if job else None,
                    "ai_optimized": crew_result["success"],
                    "generated_at": datetime.utcnow().isoformat(),
                    "customizations_applied": bool(customizations)
                },
                "html_preview": html_content[:1000] + "..." if len(html_content) > 1000 else html_content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "template_used": template_key,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    def _prepare_template_context(
        self,
        user_profile: CompleteProfile,
        job: Optional[Job],
        crew_result: Dict[str, Any],
        customizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context data for template rendering"""
        
        # Base context from user profile
        context = {
            "personal_info": user_profile.personal_info.dict() if user_profile.personal_info else {},
            "profile": user_profile.profile.dict() if user_profile.profile else {},
            "education": [edu.dict() for edu in user_profile.education] if user_profile.education else [],
            "experience": [exp.dict() for exp in user_profile.experience] if user_profile.experience else [],
            "skills": [skill.dict() for skill in user_profile.skills] if user_profile.skills else [],
            "certifications": [cert.dict() for cert in user_profile.certifications] if user_profile.certifications else [],
            "referees": [ref.dict() for ref in user_profile.referees] if user_profile.referees else [],
        }
        
        # Add AI-optimized content if available
        if crew_result.get("success") and crew_result.get("generated_content"):
            ai_content = crew_result["generated_content"]
            
            # Override with AI-optimized content
            if ai_content.get("summary"):
                context["profile"]["summary"] = ai_content["summary"]
            
            # Add AI-enhanced descriptions
            context["ai_enhanced"] = True
            context["ai_suggestions"] = ai_content.get("suggestions", [])
        
        # Add job-specific context
        if job:
            context["job_targeted"] = True
            context["target_job"] = {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "keywords": self._extract_job_keywords(job)
            }
        else:
            context["job_targeted"] = False
        
        # Apply customizations
        context.update(customizations)
        
        # Add utility data
        context.update({
            "generated_date": datetime.utcnow().strftime("%B %d, %Y"),
            "current_year": datetime.utcnow().year,
            "total_experience_years": self._calculate_experience_years(context["experience"]),
            "skill_categories": self._group_skills_by_category(context["skills"]),
            "contact_methods": self._format_contact_methods(context["personal_info"])
        })
        
        return context
    
    def _extract_job_keywords(self, job: Job) -> List[str]:
        """Extract keywords from job description for highlighting"""
        if not job.description:
            return []
        
        # Simple keyword extraction - can be enhanced with NLP
        common_keywords = [
            "python", "javascript", "react", "node", "sql", "aws", "docker",
            "leadership", "management", "agile", "scrum", "git", "api", "rest"
        ]
        
        job_text = (job.description + " " + (job.requirements or "")).lower()
        return [keyword for keyword in common_keywords if keyword in job_text]
    
    def _calculate_experience_years(self, experience: List[Dict]) -> int:
        """Calculate total years of experience"""
        total_months = 0
        for exp in experience:
            if exp.get("start_date") and exp.get("end_date"):
                try:
                    start = datetime.fromisoformat(exp["start_date"])
                    end = datetime.fromisoformat(exp["end_date"])
                    months = (end.year - start.year) * 12 + (end.month - start.month)
                    total_months += max(months, 0)
                except:
                    continue
        return max(total_months // 12, 0)
    
    def _group_skills_by_category(self, skills: List[Dict]) -> Dict[str, List[Dict]]:
        """Group skills by category"""
        categories = {}
        for skill in skills:
            category = skill.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append(skill)
        return categories
    
    def _format_contact_methods(self, personal_info: Dict) -> List[Dict[str, str]]:
        """Format contact methods for display"""
        contacts = []
        
        if personal_info.get("email"):
            contacts.append({"type": "email", "value": personal_info["email"], "icon": "envelope"})
        
        if personal_info.get("phone"):
            contacts.append({"type": "phone", "value": self._format_phone(personal_info["phone"]), "icon": "phone"})
        
        if personal_info.get("linkedin_url"):
            contacts.append({"type": "linkedin", "value": personal_info["linkedin_url"], "icon": "linkedin"})
        
        if personal_info.get("website_url"):
            contacts.append({"type": "website", "value": personal_info["website_url"], "icon": "globe"})
        
        return contacts
    
    def _render_template(self, template: CVTemplate, context: Dict[str, Any]) -> str:
        """Render HTML template with context"""
        try:
            template_obj = self.jinja_env.get_template(template.template_file)
            return template_obj.render(**context)
        except jinja2.TemplateNotFound:
            # Fallback to basic template
            return self._generate_basic_html_template(context)
    
    def _generate_basic_html_template(self, context: Dict[str, Any]) -> str:
        """Generate basic HTML template as fallback"""
        personal = context.get("personal_info", {})
        profile = context.get("profile", {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>CV - {personal.get('first_name', '')} {personal.get('last_name', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .name {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
                .contact {{ margin-bottom: 20px; }}
                .section {{ margin-bottom: 25px; }}
                .section-title {{ font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; margin-bottom: 15px; }}
                .item {{ margin-bottom: 15px; }}
                .item-title {{ font-weight: bold; }}
                .item-subtitle {{ font-style: italic; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="name">{personal.get('first_name', '')} {personal.get('last_name', '')}</div>
                <div class="contact">
                    {personal.get('email', '')} | {personal.get('phone', '')}
                </div>
            </div>
            
            {f'<div class="section"><div class="section-title">Professional Summary</div><p>{profile.get("summary", "")}</p></div>' if profile.get("summary") else ''}
            
            <div class="section">
                <div class="section-title">Experience</div>
                {''.join([f'<div class="item"><div class="item-title">{exp.get("title", "")}</div><div class="item-subtitle">{exp.get("company", "")} | {exp.get("start_date", "")} - {exp.get("end_date", "Present")}</div><p>{exp.get("description", "")}</p></div>' for exp in context.get("experience", [])])}
            </div>
            
            <div class="section">
                <div class="section-title">Education</div>
                {''.join([f'<div class="item"><div class="item-title">{edu.get("degree", "")} in {edu.get("field_of_study", "")}</div><div class="item-subtitle">{edu.get("institution", "")} | {edu.get("end_date", "")}</div></div>' for edu in context.get("education", [])])}
            </div>
            
            <div class="section">
                <div class="section-title">Skills</div>
                <p>{', '.join([skill.get('name', '') for skill in context.get('skills', [])])}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_pdf(self, html_content: str, template: CVTemplate) -> bytes:
        """Generate PDF from HTML content"""
        try:
            if WEASYPRINT_AVAILABLE:
                # Load CSS if available
                css_path = self.templates_dir / template.css_file
                css_content = ""
                
                if css_path.exists():
                    with open(css_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                
                # Generate PDF with WeasyPrint
                html_doc = HTML(string=html_content)
                css_doc = CSS(string=css_content) if css_content else None
                
                pdf_buffer = BytesIO()
                if css_doc:
                    html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
                else:
                    html_doc.write_pdf(pdf_buffer)
                
                return pdf_buffer.getvalue()
            else:
                # Use fallback PDF generator
                return self._generate_fallback_pdf(html_content)
            
        except Exception as e:
            # Fallback to basic PDF generation
            try:
                html_doc = HTML(string=html_content)
                pdf_buffer = BytesIO()
                html_doc.write_pdf(pdf_buffer)
                return pdf_buffer.getvalue()
            except Exception as e:
                # Return empty PDF as last resort
                return b"PDF generation failed"
    
    async def _save_cv_file(self, user_id: str, pdf_content: bytes, filename: str) -> tuple[str, str]:
        """Save CV file to storage and return path and URL"""
        # This would integrate with StorageService
        # For now, return mock values
        file_path = f"{user_id}/cvs/{filename}"
        pdf_url = f"https://storage.example.com/{file_path}"
        
        return file_path, pdf_url
    
    def get_available_templates(self) -> Dict[str, Dict[str, str]]:
        """Get list of available templates"""
        return {
            key: {
                "name": template.name,
                "description": template.description,
                "preview_url": f"/templates/previews/{key}.png"
            }
            for key, template in self.templates.items()
        }
    
    async def preview_template(self, template_key: str, sample_data: Optional[Dict] = None) -> str:
        """Generate HTML preview of template with sample data"""
        if template_key not in self.templates:
            raise ValueError(f"Template '{template_key}' not found")
        
        # Use sample data if provided, otherwise use default sample
        context = sample_data or self._get_sample_data()
        template = self.templates[template_key]
        
        return self._render_template(template, context)
    
    def _get_sample_data(self) -> Dict[str, Any]:
        """Get sample data for template preview"""
        return {
            "personal_info": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "(555) 123-4567",
                "city": "New York",
                "country": "USA"
            },
            "profile": {
                "headline": "Senior Software Engineer",
                "summary": "Experienced software engineer with 8+ years of expertise in full-stack development, cloud architecture, and team leadership."
            },
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                    "description": "Led development of microservices architecture serving 1M+ users daily."
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "institution": "University of Technology",
                    "end_date": "2016-05-01"
                }
            ],
            "skills": [
                {"name": "Python", "category": "Programming"},
                {"name": "React", "category": "Frontend"},
                {"name": "AWS", "category": "Cloud"}
            ]
        }


# Global service instance
cv_generator = CVGeneratorService()
