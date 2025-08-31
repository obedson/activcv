"""
Fallback PDF generator using reportlab when WeasyPrint is not available
"""

import io
from typing import Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class PDFGeneratorFallback:
    """Fallback PDF generator using reportlab"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='JobTitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=3,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Company',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=3,
            textColor=colors.darkgrey,
            fontName='Helvetica-Oblique'
        ))
    
    def generate_cv_pdf(self, cv_data: Dict[str, Any], template_name: str = "modern") -> bytes:
        """Generate CV PDF from data"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header with name and contact info
        if cv_data.get('personal_info'):
            personal = cv_data['personal_info']
            story.append(Paragraph(personal.get('full_name', ''), self.styles['CustomTitle']))
            
            contact_info = []
            if personal.get('email'):
                contact_info.append(personal['email'])
            if personal.get('phone'):
                contact_info.append(personal['phone'])
            if personal.get('location'):
                contact_info.append(personal['location'])
            
            if contact_info:
                story.append(Paragraph(' | '.join(contact_info), self.styles['Normal']))
            
            story.append(Spacer(1, 12))
        
        # Professional Summary
        if cv_data.get('professional_summary'):
            story.append(Paragraph('Professional Summary', self.styles['SectionHeader']))
            story.append(Paragraph(cv_data['professional_summary'], self.styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Work Experience
        if cv_data.get('work_experience'):
            story.append(Paragraph('Work Experience', self.styles['SectionHeader']))
            for job in cv_data['work_experience']:
                story.append(Paragraph(job.get('job_title', ''), self.styles['JobTitle']))
                story.append(Paragraph(f"{job.get('company', '')} | {job.get('duration', '')}", 
                                     self.styles['Company']))
                if job.get('description'):
                    story.append(Paragraph(job['description'], self.styles['Normal']))
                story.append(Spacer(1, 8))
        
        # Education
        if cv_data.get('education'):
            story.append(Paragraph('Education', self.styles['SectionHeader']))
            for edu in cv_data['education']:
                story.append(Paragraph(f"{edu.get('degree', '')} - {edu.get('institution', '')}", 
                                     self.styles['JobTitle']))
                if edu.get('year'):
                    story.append(Paragraph(edu['year'], self.styles['Company']))
                story.append(Spacer(1, 8))
        
        # Skills
        if cv_data.get('skills'):
            story.append(Paragraph('Skills', self.styles['SectionHeader']))
            skills_text = ', '.join(cv_data['skills']) if isinstance(cv_data['skills'], list) else cv_data['skills']
            story.append(Paragraph(skills_text, self.styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_cover_letter_pdf(self, cover_letter_data: Dict[str, Any]) -> bytes:
        """Generate cover letter PDF from data"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        if cover_letter_data.get('applicant_name'):
            story.append(Paragraph(cover_letter_data['applicant_name'], self.styles['CustomTitle']))
            story.append(Spacer(1, 12))
        
        # Date
        story.append(Paragraph(cover_letter_data.get('date', ''), self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Recipient
        if cover_letter_data.get('recipient'):
            story.append(Paragraph(cover_letter_data['recipient'], self.styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Content
        if cover_letter_data.get('content'):
            paragraphs = cover_letter_data['content'].split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['Normal']))
                    story.append(Spacer(1, 12))
        
        # Signature
        story.append(Spacer(1, 24))
        story.append(Paragraph('Sincerely,', self.styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(cover_letter_data.get('applicant_name', ''), self.styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
