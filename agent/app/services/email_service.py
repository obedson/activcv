"""
Email delivery service for CV notifications and communications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import jinja2
from pathlib import Path

from app.core.config import settings
from app.models.jobs import Job, GeneratedCV
from app.models.profile import CompleteProfile


class EmailTemplate:
    """Email template configuration"""
    
    def __init__(self, name: str, subject: str, template_file: str, description: str):
        self.name = name
        self.subject = subject
        self.template_file = template_file
        self.description = description


class EmailService:
    """Service for sending emails and notifications"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates" / "email"
        self.templates = self._load_email_templates()
        self.jinja_env = self._setup_jinja_environment()
        self.email_provider = self._determine_email_provider()
    
    def _load_email_templates(self) -> Dict[str, EmailTemplate]:
        """Load available email templates"""
        return {
            "cv_generated": EmailTemplate(
                name="CV Generated",
                subject="Your CV is Ready! 📄",
                template_file="cv_generated.html",
                description="Notification when CV generation is complete"
            ),
            "cv_generation_failed": EmailTemplate(
                name="CV Generation Failed",
                subject="CV Generation Issue - We're Here to Help",
                template_file="cv_generation_failed.html",
                description="Notification when CV generation fails"
            ),
            "cover_letter_ready": EmailTemplate(
                name="Cover Letter Ready",
                subject="Your Cover Letter is Ready! 📄",
                template_file="cover_letter_ready.html",
                description="Notification when cover letter generation is complete"
            ),
            "cover_letter_error": EmailTemplate(
                name="Cover Letter Error",
                subject="Cover Letter Generation Issue",
                template_file="cover_letter_error.html",
                description="Notification when cover letter generation fails"
            ),
            "job_suggestions": EmailTemplate(
                name="New Job Suggestions",
                subject="New Job Matches Found! 🎯",
                template_file="job_suggestions.html",
                description="Weekly digest of new job suggestions"
            ),
            "welcome": EmailTemplate(
                name="Welcome Email",
                subject="Welcome to AI CV Agent! 🚀",
                template_file="welcome.html",
                description="Welcome email for new users"
            ),
            "cv_tips": EmailTemplate(
                name="CV Tips",
                subject="Tips to Improve Your CV 💡",
                template_file="cv_tips.html",
                description="Helpful tips for CV improvement"
            ),
            "job_application_reminder": EmailTemplate(
                name="Application Reminder",
                subject="Don't Forget to Apply! ⏰",
                template_file="job_application_reminder.html",
                description="Reminder to apply for suggested jobs"
            )
        }
    
    def _setup_jinja_environment(self) -> jinja2.Environment:
        """Setup Jinja2 template environment for emails"""
        loader = jinja2.FileSystemLoader(str(self.templates_dir))
        env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        env.filters['format_date'] = self._format_date
        env.filters['format_currency'] = self._format_currency
        env.filters['truncate_text'] = self._truncate_text
        
        return env
    
    def _determine_email_provider(self) -> str:
        """Determine which email provider to use"""
        if settings.RESEND_API_KEY:
            return "resend"
        elif settings.SENDGRID_API_KEY:
            return "sendgrid"
        elif settings.SMTP_HOST:
            return "smtp"
        else:
            return "mock"  # For development/testing
    
    def _format_date(self, date_str: str) -> str:
        """Format date for email display"""
        if not date_str:
            return ""
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime("%B %d, %Y")
        except:
            return date_str
    
    def _format_currency(self, amount: str) -> str:
        """Format currency for display"""
        if not amount:
            return ""
        # Simple formatting - can be enhanced
        return f"${amount}"
    
    def _truncate_text(self, text: str, length: int = 100) -> str:
        """Truncate text to specified length"""
        if not text:
            return ""
        return text[:length] + "..." if len(text) > length else text
    
    async def send_cv_generated_notification(
        self,
        user_email: str,
        user_name: str,
        generated_cv: GeneratedCV,
        job: Optional[Job] = None
    ) -> Dict[str, Any]:
        """Send notification when CV is successfully generated"""
        
        context = {
            "user_name": user_name,
            "cv_id": generated_cv.id,
            "template_used": generated_cv.template_used,
            "generated_date": generated_cv.created_at,
            "download_url": generated_cv.pdf_url,
            "file_size": self._format_file_size(generated_cv.file_size),
            "job_targeted": job is not None,
            "job": job.dict() if job else None,
            "tips": self._get_cv_tips(),
            "support_email": "support@aicvagent.com"
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="cv_generated",
            context=context,
            attachments=[]  # CV will be downloaded via secure link
        )
    
    async def send_cv_generation_failed_notification(
        self,
        user_email: str,
        user_name: str,
        error_message: str,
        job: Optional[Job] = None
    ) -> Dict[str, Any]:
        """Send notification when CV generation fails"""
        
        context = {
            "user_name": user_name,
            "error_message": error_message,
            "job": job.dict() if job else None,
            "support_email": "support@aicvagent.com",
            "retry_url": "https://app.aicvagent.com/profile",
            "troubleshooting_tips": self._get_troubleshooting_tips()
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="cv_generation_failed",
            context=context
        )
    
    async def send_job_suggestions_digest(
        self,
        user_email: str,
        user_name: str,
        suggested_jobs: List[Dict[str, Any]],
        stats: Dict[str, int]
    ) -> Dict[str, Any]:
        """Send weekly digest of job suggestions"""
        
        context = {
            "user_name": user_name,
            "suggested_jobs": suggested_jobs[:10],  # Limit to top 10
            "total_suggestions": len(suggested_jobs),
            "stats": stats,
            "week_period": self._get_week_period(),
            "dashboard_url": "https://app.aicvagent.com/jobs",
            "unsubscribe_url": "https://app.aicvagent.com/unsubscribe"
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="job_suggestions",
            context=context
        )
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Send welcome email to new users"""
        
        context = {
            "user_name": user_name,
            "getting_started_url": "https://app.aicvagent.com/profile",
            "features": [
                "AI-powered CV generation",
                "Job site monitoring",
                "Intelligent job matching",
                "Multiple professional templates",
                "ATS optimization"
            ],
            "support_email": "support@aicvagent.com",
            "tutorial_url": "https://app.aicvagent.com/tutorial"
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="welcome",
            context=context
        )
    
    async def send_application_reminder(
        self,
        user_email: str,
        user_name: str,
        pending_jobs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send reminder to apply for suggested jobs"""
        
        context = {
            "user_name": user_name,
            "pending_jobs": pending_jobs[:5],  # Limit to top 5
            "total_pending": len(pending_jobs),
            "dashboard_url": "https://app.aicvagent.com/jobs/suggestions",
            "tips": self._get_application_tips()
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="job_application_reminder",
            context=context
        )
    
    async def send_cover_letter_ready_notification(
        self,
        user_email: str,
        user_name: str,
        job_title: str,
        company_name: str,
        cover_letter_url: str,
        generation_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send notification when cover letter is ready"""
        
        context = {
            "user_name": user_name,
            "job_title": job_title,
            "company_name": company_name,
            "cover_letter_url": cover_letter_url,
            "generation_time": generation_time or "< 1000",
            "dashboard_url": "https://app.aicvagent.com/cover-letters",
            "support_email": "support@aicvagent.com"
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="cover_letter_ready",
            context=context
        )
    
    async def send_cover_letter_error_notification(
        self,
        user_email: str,
        user_name: str,
        job_title: str,
        company_name: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Send notification when cover letter generation fails"""
        
        context = {
            "user_name": user_name,
            "job_title": job_title,
            "company_name": company_name,
            "error_message": error_message,
            "retry_url": "https://app.aicvagent.com/jobs",
            "profile_url": "https://app.aicvagent.com/profile",
            "support_email": "support@aicvagent.com",
            "troubleshooting_tips": self._get_cover_letter_troubleshooting_tips()
        }
        
        return await self._send_email(
            to_email=user_email,
            template_key="cover_letter_error",
            context=context
        )
    
    async def _send_email(
        self,
        to_email: str,
        template_key: str,
        context: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email using configured provider"""
        
        if template_key not in self.templates:
            return {"success": False, "error": f"Template '{template_key}' not found"}
        
        template = self.templates[template_key]
        
        try:
            # Render email content
            html_content = self._render_email_template(template, context)
            text_content = self._html_to_text(html_content)
            
            # Send based on provider
            if self.email_provider == "resend":
                result = await self._send_via_resend(
                    to_email=to_email,
                    subject=template.subject,
                    html_content=html_content,
                    text_content=text_content,
                    attachments=attachments
                )
            elif self.email_provider == "sendgrid":
                result = await self._send_via_sendgrid(
                    to_email=to_email,
                    subject=template.subject,
                    html_content=html_content,
                    text_content=text_content,
                    attachments=attachments
                )
            elif self.email_provider == "smtp":
                result = await self._send_via_smtp(
                    to_email=to_email,
                    subject=template.subject,
                    html_content=html_content,
                    text_content=text_content,
                    attachments=attachments
                )
            else:
                # Mock provider for development
                result = await self._send_via_mock(
                    to_email=to_email,
                    subject=template.subject,
                    html_content=html_content
                )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.email_provider,
                "template": template_key
            }
    
    def _render_email_template(self, template: EmailTemplate, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        try:
            template_obj = self.jinja_env.get_template(template.template_file)
            return template_obj.render(**context)
        except jinja2.TemplateNotFound:
            # Fallback to basic template
            return self._generate_basic_email_template(template.subject, context)
    
    def _generate_basic_email_template(self, subject: str, context: Dict[str, Any]) -> str:
        """Generate basic email template as fallback"""
        user_name = context.get("user_name", "User")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>AI CV Agent</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>{subject}</p>
                    <p>Thank you for using AI CV Agent. We're here to help you succeed in your job search.</p>
                </div>
                <div class="footer">
                    <p>© 2024 AI CV Agent. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        # Simple HTML to text conversion - can be enhanced with libraries like BeautifulSoup
        import re
        text = re.sub('<[^<]+?>', '', html_content)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via Resend API"""
        
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": settings.FROM_EMAIL or "noreply@aicvagent.com",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": text_content
        }
        
        # Add attachments if provided
        if attachments:
            payload["attachments"] = attachments
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                "success": True,
                "provider": "resend",
                "message_id": response.json().get("id"),
                "to": to_email
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "provider": "resend",
                "error": str(e),
                "to": to_email
            }
    
    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid API"""
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "personalizations": [{
                "to": [{"email": to_email}],
                "subject": subject
            }],
            "from": {"email": settings.FROM_EMAIL or "noreply@aicvagent.com"},
            "content": [
                {"type": "text/plain", "value": text_content},
                {"type": "text/html", "value": html_content}
            ]
        }
        
        # Add attachments if provided
        if attachments:
            payload["attachments"] = attachments
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                "success": True,
                "provider": "sendgrid",
                "message_id": response.headers.get("X-Message-Id"),
                "to": to_email
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "provider": "sendgrid",
                "error": str(e),
                "to": to_email
            }
    
    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP"""
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.FROM_EMAIL or "noreply@aicvagent.com"
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                
                server.send_message(msg)
            
            return {
                "success": True,
                "provider": "smtp",
                "to": to_email
            }
            
        except Exception as e:
            return {
                "success": False,
                "provider": "smtp",
                "error": str(e),
                "to": to_email
            }
    
    async def _send_via_mock(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> Dict[str, Any]:
        """Mock email sending for development"""
        
        print(f"📧 MOCK EMAIL SENT")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Content: {html_content[:200]}...")
        print("=" * 50)
        
        return {
            "success": True,
            "provider": "mock",
            "message_id": f"mock_{datetime.utcnow().timestamp()}",
            "to": to_email
        }
    
    def _format_file_size(self, size_bytes: Optional[int]) -> str:
        """Format file size for display"""
        if not size_bytes:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _get_cv_tips(self) -> List[str]:
        """Get CV improvement tips"""
        return [
            "Use action verbs to describe your achievements",
            "Quantify your accomplishments with numbers and percentages",
            "Tailor your CV for each job application",
            "Keep your CV to 1-2 pages maximum",
            "Use a clean, professional format that's ATS-friendly"
        ]
    
    def _get_troubleshooting_tips(self) -> List[str]:
        """Get troubleshooting tips for failed CV generation"""
        return [
            "Ensure your profile is complete with all required sections",
            "Check that your experience descriptions are detailed",
            "Verify that dates are in the correct format",
            "Try using a different CV template",
            "Contact support if the issue persists"
        ]
    
    def _get_application_tips(self) -> List[str]:
        """Get job application tips"""
        return [
            "Apply within 24-48 hours of job posting for best results",
            "Customize your CV for each application",
            "Write a compelling cover letter",
            "Follow up after 1-2 weeks if you haven't heard back",
            "Research the company before applying"
        ]
    
    def _get_cover_letter_troubleshooting_tips(self) -> List[str]:
        """Get troubleshooting tips for failed cover letter generation"""
        return [
            "Ensure your profile includes detailed work experience",
            "Check that the job description has sufficient information",
            "Try using the 'Professional Standard' template",
            "Verify your skills and achievements are up to date",
            "Contact support if the issue persists"
        ]
    
    def _get_week_period(self) -> str:
        """Get current week period for digest emails"""
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        return f"{week_start.strftime('%B %d')} - {now.strftime('%B %d, %Y')}"
    
    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        template_key: str,
        base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send bulk emails to multiple recipients"""
        
        results = {
            "total_sent": 0,
            "total_failed": 0,
            "successes": [],
            "failures": []
        }
        
        for recipient in recipients:
            try:
                # Merge base context with recipient-specific context
                context = {**base_context, **recipient.get("context", {})}
                
                result = await self._send_email(
                    to_email=recipient["email"],
                    template_key=template_key,
                    context=context
                )
                
                if result["success"]:
                    results["total_sent"] += 1
                    results["successes"].append(recipient["email"])
                else:
                    results["total_failed"] += 1
                    results["failures"].append({
                        "email": recipient["email"],
                        "error": result.get("error")
                    })
                    
            except Exception as e:
                results["total_failed"] += 1
                results["failures"].append({
                    "email": recipient.get("email", "unknown"),
                    "error": str(e)
                })
        
        return results


# Global service instance
email_service = EmailService()