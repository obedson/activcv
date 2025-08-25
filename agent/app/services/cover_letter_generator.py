"""
Cover letter generation service with AI-powered content creation
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import jinja2
from weasyprint import HTML, CSS
from io import BytesIO

from app.services.crew_agents import crew_service
from app.core.config import settings


class CoverLetterTemplate:
    """Cover letter template configuration"""
    
    def __init__(self, name: str, template_file: str, css_file: str, description: str, tone: str = "professional"):
        self.name = name
        self.template_file = template_file
        self.css_file = css_file
        self.description = description
        self.tone = tone


class CoverLetterGeneratorService:
    """Service for generating personalized cover letters with AI"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "cover_letter"
        self.templates = self._load_templates()
        self.jinja_env = self._setup_jinja_environment()
    
    def _load_templates(self) -> Dict[str, CoverLetterTemplate]:
        """Load available cover letter templates"""
        return {
            "professional_standard": CoverLetterTemplate(
                name="Professional Standard",
                template_file="professional_standard.html",
                css_file="professional_standard.css",
                description="Classic professional format suitable for most industries",
                tone="professional"
            ),
            "modern_creative": CoverLetterTemplate(
                name="Modern Creative",
                template_file="modern_creative.html",
                css_file="modern_creative.css",
                description="Contemporary design for creative and tech industries",
                tone="modern"
            ),
            "executive_formal": CoverLetterTemplate(
                name="Executive Formal",
                template_file="executive_formal.html",
                css_file="executive_formal.css",
                description="Formal executive style for senior positions",
                tone="formal"
            ),
            "startup_casual": CoverLetterTemplate(
                name="Startup Casual",
                template_file="startup_casual.html",
                css_file="startup_casual.css",
                description="Casual, personable tone for startup environments",
                tone="casual"
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
        env.filters['capitalize_words'] = self._capitalize_words
        
        return env
    
    def _format_date(self, date_str: str) -> str:
        """Format date for cover letter display"""
        if not date_str:
            return datetime.utcnow().strftime("%B %d, %Y")
        try:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date_obj = date_str
            return date_obj.strftime("%B %d, %Y")
        except:
            return date_str
    
    def _capitalize_words(self, text: str) -> str:
        """Capitalize each word in text"""
        return ' '.join(word.capitalize() for word in text.split())
    
    async def generate_cover_letter(
        self,
        job_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        template_key: str = "professional_standard",
        customizations: Optional[Dict[str, Any]] = None,
        max_length: int = 400
    ) -> Dict[str, Any]:
        """Generate a complete cover letter with AI optimization"""
        
        try:
            # Validate template
            if template_key not in self.templates:
                raise ValueError(f"Template '{template_key}' not found")
            
            template = self.templates[template_key]
            
            # Use CrewAI for content generation
            crew_result = await crew_service.process_cover_letter_generation(
                user_profile=user_profile,
                job_data=job_data,
                template_tone=template.tone,
                max_length=max_length,
                customizations=customizations or {}
            )
            
            if not crew_result.get("success"):
                raise Exception(f"AI content generation failed: {crew_result.get('error')}")
            
            # Prepare template context
            context = self._prepare_template_context(
                user_profile=user_profile,
                job_data=job_data,
                crew_result=crew_result,
                customizations=customizations or {}
            )
            
            # Generate HTML
            html_content = self._render_template(template, context)
            
            # Generate PDF
            pdf_content = self._generate_pdf(html_content, template)
            
            # Save to storage
            user_id = user_profile.get("user_id") or user_profile.get("id")
            filename = f"cover_letter_{template_key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            file_path, pdf_url = await self._save_cover_letter_file(
                user_id=user_id,
                pdf_content=pdf_content,
                filename=filename
            )
            
            return {
                "success": True,
                "pdf_url": pdf_url,
                "file_path": file_path,
                "file_size": len(pdf_content),
                "template_used": template_key,
                "word_count": self._count_words(crew_result.get("generated_content", {})),
                "content": crew_result.get("generated_content", {}),
                "metadata": {
                    "template": template_key,
                    "job_id": job_data.get("id"),
                    "job_title": job_data.get("title"),
                    "company": job_data.get("company"),
                    "ai_optimized": crew_result.get("success", False),
                    "generated_at": datetime.utcnow().isoformat(),
                    "customizations_applied": bool(customizations)
                }
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
        user_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        crew_result: Dict[str, Any],
        customizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context data for template rendering"""
        
        # Extract personal info
        personal_info = user_profile.get("personal_info", {})
        if isinstance(personal_info, dict):
            personal = personal_info
        else:
            personal = personal_info.__dict__ if hasattr(personal_info, '__dict__') else {}
        
        # Base context
        context = {
            "personal_info": personal,
            "job": job_data,
            "current_date": datetime.utcnow().strftime("%B %d, %Y"),
            "hiring_manager": customizations.get("hiring_manager", "Hiring Manager")
        }
        
        # Add AI-generated content
        if crew_result.get("success") and crew_result.get("generated_content"):
            context["ai_content"] = crew_result["generated_content"]
        else:
            # Fallback content
            context["ai_content"] = self._generate_fallback_content(job_data, personal)
        
        # Apply customizations
        context.update(customizations)
        
        return context
    
    def _generate_fallback_content(self, job_data: Dict[str, Any], personal: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback content when AI generation fails"""
        job_title = job_data.get("title", "position")
        company = job_data.get("company", "your company")
        
        return {
            "opening_paragraph": f"I am writing to express my strong interest in the {job_title} position at {company}. With my background and experience, I am confident I can make a valuable contribution to your team.",
            "body_paragraph_1": "My professional experience has equipped me with the skills and knowledge necessary to excel in this role. I have a proven track record of delivering results and working effectively in collaborative environments.",
            "body_paragraph_2": f"I am particularly drawn to {company} because of your reputation for innovation and excellence. I am excited about the opportunity to contribute to your continued success and growth.",
            "closing_paragraph": "Thank you for considering my application. I would welcome the opportunity to discuss how my skills and enthusiasm can benefit your organization. I look forward to hearing from you."
        }
    
    def _count_words(self, content: Dict[str, Any]) -> int:
        """Count words in generated content"""
        total_words = 0
        for value in content.values():
            if isinstance(value, str):
                total_words += len(value.split())
        return total_words
    
    def _render_template(self, template: CoverLetterTemplate, context: Dict[str, Any]) -> str:
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
        job = context.get("job", {})
        ai_content = context.get("ai_content", {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Cover Letter</title>     
       <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
                .header { margin-bottom: 30px; }
                .sender-info { margin-bottom: 20px; }
                .date { margin-bottom: 20px; }
                .recipient-info { margin-bottom: 30px; }
                .content { margin-bottom: 30px; }
                .paragraph { margin-bottom: 15px; text-align: justify; }
                .signature { margin-top: 30px; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="sender-info">
                    <strong>{personal.get('first_name', '')} {personal.get('last_name', '')}</strong><br>
                    {personal.get('email', '')}<br>
                    {personal.get('phone', '')}<br>
                    {personal.get('city', '')}, {personal.get('country', '')}
                </div>
                
                <div class="date">{context.get('current_date', '')}</div>
                
                <div class="recipient-info">
                    {context.get('hiring_manager', 'Hiring Manager')}<br>
                    {job.get('company', '')}<br>
                    {job.get('location', '')}
                </div>
            </div>
            
            <div class="content">
                <p class="paragraph">Dear {context.get('hiring_manager', 'Hiring Manager')},</p>
                
                <p class="paragraph">{ai_content.get('opening_paragraph', 'I am writing to express my interest in the ' + job.get('title', 'position') + ' at ' + job.get('company', 'your company') + '.')}</p>
                
                <p class="paragraph">{ai_content.get('body_paragraph_1', 'My experience and skills align well with your requirements.')}</p>
                
                <p class="paragraph">{ai_content.get('body_paragraph_2', 'I am excited about the opportunity to contribute to your team.')}</p>
                
                <p class="paragraph">{ai_content.get('closing_paragraph', 'Thank you for considering my application. I look forward to hearing from you.')}</p>
                
                <div class="signature">
                    Sincerely,<br><br>
                    <strong>{personal.get('first_name', '')} {personal.get('last_name', '')}</strong>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_pdf(self, html_content: str, template: CoverLetterTemplate) -> bytes:
        """Generate PDF from HTML content"""
        try:
            # Load CSS if available
            css_path = self.templates_dir / template.css_file
            css_content = ""
            
            if css_path.exists():
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
            
            # Generate PDF
            html_doc = HTML(string=html_content)
            css_doc = CSS(string=css_content) if css_content else None
            
            pdf_buffer = BytesIO()
            if css_doc:
                html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
            else:
                html_doc.write_pdf(pdf_buffer)
            
            return pdf_buffer.getvalue()
            
        except Exception as e:
            # Fallback to basic PDF generation
            return self._generate_basic_pdf(html_content)
    
    def _generate_basic_pdf(self, html_content: str) -> bytes:
        """Generate basic PDF as fallback"""
        try:
            html_doc = HTML(string=html_content)
            pdf_buffer = BytesIO()
            html_doc.write_pdf(pdf_buffer)
            return pdf_buffer.getvalue()
        except Exception as e:
            # Return placeholder content
            return b"Cover letter PDF generation failed"
    
    async def _save_cover_letter_file(self, user_id: str, pdf_content: bytes, filename: str) -> tuple[str, str]:
        """Save cover letter file to storage and return path and URL"""
        try:
            from app.services.storage import StorageService
            from app.core.database import get_db
            
            # Initialize storage service
            db = get_db()
            storage_service = StorageService(db)
            
            # Upload file to storage
            file_path = f"{user_id}/cover_letters/{filename}"
            
            # Upload the PDF content
            upload_result = await storage_service.upload_file(
                user_id=user_id,
                file_content=pdf_content,
                file_name=filename,
                content_type="application/pdf",
                folder="cover_letters"
            )
            
            if upload_result["success"]:
                return upload_result["file_path"], upload_result["public_url"]
            else:
                raise Exception(f"Storage upload failed: {upload_result.get('error')}")
                
        except Exception as e:
            # Fallback: save to local storage or return error
            print(f"Storage service error: {e}")
            # For development, you might want to save locally
            import os
            local_dir = f"./temp_storage/{user_id}/cover_letters"
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, filename)
            
            with open(local_path, 'wb') as f:
                f.write(pdf_content)
            
            return local_path, f"file://{local_path}"
    
    def get_available_templates(self) -> Dict[str, Dict[str, str]]:
        """Get list of available cover letter templates"""
        return {
            key: {
                "name": template.name,
                "description": template.description,
                "tone": template.tone,
                "preview_url": f"/templates/cover_letter_previews/{key}.png"
            }
            for key, template in self.templates.items()
        }
    
    async def preview_template(self, template_key: str, sample_data: Optional[Dict] = None) -> str:
        """Generate HTML preview of cover letter template"""
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
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
                "phone": "(555) 987-6543",
                "city": "San Francisco",
                "country": "USA"
            },
            "job": {
                "title": "Senior Product Manager",
                "company": "Innovation Corp",
                "location": "San Francisco, CA"
            },
            "ai_content": {
                "opening_paragraph": "I am excited to apply for the Senior Product Manager position at Innovation Corp. With over 6 years of product management experience and a proven track record of launching successful products, I am confident I can drive meaningful impact for your team.",
                "body_paragraph_1": "In my current role as Product Manager at TechStart, I led the development and launch of three major product features that increased user engagement by 40% and revenue by $2M annually. I excel at translating complex technical requirements into clear product roadmaps and working cross-functionally with engineering, design, and marketing teams.",
                "body_paragraph_2": "My expertise in data-driven decision making, user research, and agile methodologies aligns perfectly with Innovation Corp's focus on customer-centric product development. I am particularly drawn to your company's mission of democratizing technology and would love to contribute to products that make a real difference in users' lives.",
                "closing_paragraph": "I would welcome the opportunity to discuss how my product management experience and passion for innovation can help drive Innovation Corp's continued growth. Thank you for considering my application, and I look forward to hearing from you."
            },
            "current_date": datetime.utcnow().strftime("%B %d, %Y"),
            "hiring_manager": "Hiring Manager"
        }


# Global service instance
cover_letter_generator = CoverLetterGeneratorService()