"""
CV parsing service for extracting structured data from PDFs
"""

import re
import io
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pypdf
from supabase import Client
from app.models.upload import ParsedData
from app.services.storage import StorageService


class CVParserService:
    """Service for parsing CV content and extracting structured data"""
    
    def __init__(self, db: Client):
        self.db = db
        self.storage_service = StorageService(db)
    
    async def extract_text_from_pdf(self, file_path: str, user_id: str) -> str:
        """Extract raw text from PDF file"""
        try:
            # Get signed URL for the file
            signed_url = await self.storage_service.get_signed_url(user_id, file_path)
            
            # Download and parse PDF
            import requests
            response = requests.get(signed_url)
            response.raise_for_status()
            
            pdf_reader = pypdf.PdfReader(io.BytesIO(response.content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def parse_personal_info(self, text: str) -> Dict[str, Any]:
        """Extract personal information from CV text"""
        personal_info = {}
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            personal_info['email'] = emails[0]
        
        # Phone extraction
        phone_patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?([0-9]{1,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                if isinstance(phones[0], tuple):
                    personal_info['phone'] = ''.join(phones[0])
                else:
                    personal_info['phone'] = phones[0]
                break
        
        # Name extraction (first few lines, excluding email/phone)
        lines = text.split('\n')[:5]
        for line in lines:
            line = line.strip()
            if line and not re.search(email_pattern, line) and not any(char.isdigit() for char in line):
                if len(line.split()) >= 2 and len(line) < 50:
                    name_parts = line.split()
                    if len(name_parts) >= 2:
                        personal_info['first_name'] = name_parts[0]
                        personal_info['last_name'] = ' '.join(name_parts[1:])
                        break
        
        # LinkedIn URL
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_matches:
            personal_info['linkedin_url'] = f"https://{linkedin_matches[0]}"
        
        return personal_info
    
    def parse_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information from CV text"""
        education = []
        
        # Look for education section
        education_section = self._extract_section(text, ['education', 'academic', 'qualification'])
        if not education_section:
            return education
        
        # Common degree patterns
        degree_patterns = [
            r'(Bachelor|Master|PhD|Doctorate|Associate|Diploma|Certificate).*?(?:in|of)\s+([^,\n]+)',
            r'(B\.?A\.?|B\.?S\.?|M\.?A\.?|M\.?S\.?|Ph\.?D\.?|MBA)\s*(?:in|of)?\s*([^,\n]+)',
            r'(Bachelor|Master|PhD|Doctorate)\s+([^,\n]+)'
        ]
        
        # Institution patterns
        institution_patterns = [
            r'(?:at|from)\s+([A-Z][^,\n]+(?:University|College|Institute|School))',
            r'([A-Z][^,\n]+(?:University|College|Institute|School))'
        ]
        
        # Year patterns
        year_pattern = r'\b(19|20)\d{2}\b'
        
        lines = education_section.split('\n')
        current_education = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_education:
                    education.append(current_education)
                    current_education = {}
                continue
            
            # Check for degree
            for pattern in degree_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    current_education['degree'] = match.group(1)
                    current_education['field_of_study'] = match.group(2).strip()
                    break
            
            # Check for institution
            for pattern in institution_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    current_education['institution'] = match.group(1).strip()
                    break
            
            # Check for years
            years = re.findall(year_pattern, line)
            if years:
                years = [int(y) for y in years]
                if len(years) >= 2:
                    current_education['start_date'] = f"{min(years)}-01-01"
                    current_education['end_date'] = f"{max(years)}-12-31"
                elif len(years) == 1:
                    current_education['end_date'] = f"{years[0]}-12-31"
        
        if current_education:
            education.append(current_education)
        
        return education
    
    def parse_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience from CV text"""
        experience = []
        
        # Look for experience section
        experience_section = self._extract_section(text, ['experience', 'employment', 'work', 'career'])
        if not experience_section:
            return experience
        
        # Job title patterns
        title_patterns = [
            r'^([A-Z][^,\n]+(?:Engineer|Developer|Manager|Analyst|Specialist|Coordinator|Director|Lead))',
            r'^([A-Z][^,\n]+)\s+(?:at|@)\s+',
            r'^([A-Z][A-Za-z\s]+)(?:\s*[-–]\s*|\s+at\s+)'
        ]
        
        # Company patterns
        company_patterns = [
            r'(?:at|@)\s+([A-Z][^,\n]+?)(?:\s*[-–]\s*|\s*,|\s*\n)',
            r'([A-Z][^,\n]+(?:Inc|LLC|Corp|Company|Ltd|Limited))'
        ]
        
        # Year patterns
        year_pattern = r'\b(19|20)\d{2}\b'
        
        lines = experience_section.split('\n')
        current_job = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_job:
                    experience.append(current_job)
                    current_job = {}
                continue
            
            # Check for job title
            for pattern in title_patterns:
                match = re.search(pattern, line)
                if match:
                    current_job['title'] = match.group(1).strip()
                    break
            
            # Check for company
            for pattern in company_patterns:
                match = re.search(pattern, line)
                if match:
                    current_job['company'] = match.group(1).strip()
                    break
            
            # Check for years
            years = re.findall(year_pattern, line)
            if years:
                years = [int(y) for y in years]
                if len(years) >= 2:
                    current_job['start_date'] = f"{min(years)}-01-01"
                    current_job['end_date'] = f"{max(years)}-12-31"
                elif len(years) == 1:
                    current_job['start_date'] = f"{years[0]}-01-01"
            
            # Collect description lines
            if 'description' not in current_job:
                current_job['description'] = ""
            if not any(re.search(pattern, line) for pattern in title_patterns + company_patterns):
                if not re.search(year_pattern, line):
                    current_job['description'] += line + " "
        
        if current_job:
            experience.append(current_job)
        
        # Clean up descriptions
        for job in experience:
            if 'description' in job:
                job['description'] = job['description'].strip()
        
        return experience
    
    def parse_skills(self, text: str) -> List[Dict[str, Any]]:
        """Extract skills from CV text"""
        skills = []
        
        # Look for skills section
        skills_section = self._extract_section(text, ['skills', 'technical', 'competencies', 'technologies'])
        if not skills_section:
            # Fallback: look for common technical terms throughout the document
            skills_section = text
        
        # Common skill categories and keywords
        skill_categories = {
            'Programming Languages': [
                'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust',
                'TypeScript', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB'
            ],
            'Web Technologies': [
                'HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django',
                'Flask', 'Spring', 'Laravel', 'Bootstrap', 'jQuery'
            ],
            'Databases': [
                'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
                'Elasticsearch', 'Cassandra', 'DynamoDB'
            ],
            'Cloud & DevOps': [
                'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'CI/CD',
                'Terraform', 'Ansible'
            ],
            'Data Science': [
                'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas',
                'NumPy', 'Scikit-learn', 'Jupyter', 'Tableau', 'Power BI'
            ]
        }
        
        found_skills = set()
        
        for category, skill_list in skill_categories.items():
            for skill in skill_list:
                # Case-insensitive search with word boundaries
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, skills_section, re.IGNORECASE):
                    found_skills.add((skill, category))
        
        # Convert to list of dictionaries
        for skill, category in found_skills:
            skills.append({
                'name': skill,
                'category': category,
                'level': 'intermediate'  # Default level
            })
        
        return skills
    
    def parse_certifications(self, text: str) -> List[Dict[str, Any]]:
        """Extract certifications from CV text"""
        certifications = []
        
        # Look for certifications section
        cert_section = self._extract_section(text, ['certifications', 'certificates', 'licenses', 'credentials'])
        if not cert_section:
            # Fallback: search entire document for certification patterns
            cert_section = text
        
        # Common certification patterns and providers
        cert_patterns = {
            # Cloud Certifications
            'AWS': [
                'AWS Certified Solutions Architect', 'AWS Certified Developer', 'AWS Certified SysOps Administrator',
                'AWS Certified DevOps Engineer', 'AWS Certified Security', 'AWS Certified Data Analytics',
                'AWS Certified Machine Learning', 'AWS Certified Database', 'AWS Cloud Practitioner'
            ],
            'Microsoft Azure': [
                'Azure Fundamentals', 'Azure Administrator', 'Azure Developer', 'Azure Solutions Architect',
                'Azure DevOps Engineer', 'Azure Security Engineer', 'Azure Data Engineer', 'Azure AI Engineer'
            ],
            'Google Cloud': [
                'Google Cloud Professional', 'Google Cloud Associate', 'GCP Cloud Architect',
                'GCP Data Engineer', 'GCP DevOps Engineer', 'GCP Security Engineer'
            ],
            
            # Programming & Development
            'Oracle': [
                'Oracle Certified Professional', 'Oracle Certified Associate', 'Oracle Java Programmer',
                'Oracle Database Administrator', 'OCP', 'OCA'
            ],
            'Microsoft': [
                'Microsoft Certified', 'MCSA', 'MCSE', 'MCSD', 'Microsoft Azure', 'Microsoft 365'
            ],
            'Cisco': [
                'CCNA', 'CCNP', 'CCIE', 'Cisco Certified', 'CCDA', 'CCDP'
            ],
            
            # Project Management
            'PMI': [
                'PMP', 'Project Management Professional', 'CAPM', 'PMI-ACP', 'PMI-RMP', 'PMI-SP'
            ],
            'Scrum': [
                'Certified Scrum Master', 'CSM', 'Certified Scrum Product Owner', 'CSPO',
                'Professional Scrum Master', 'PSM', 'Scrum Alliance'
            ],
            
            # Security
            'Security': [
                'CISSP', 'CISM', 'CISA', 'CompTIA Security+', 'CEH', 'Certified Ethical Hacker',
                'GSEC', 'CISSP', 'CCSP'
            ],
            
            # Data & Analytics
            'Data Science': [
                'Certified Analytics Professional', 'CAP', 'Tableau Certified', 'SAS Certified',
                'Cloudera Certified', 'Databricks Certified', 'Snowflake Certified'
            ],
            
            # Industry Specific
            'Finance': [
                'CFA', 'FRM', 'CPA', 'Chartered Financial Analyst', 'Financial Risk Manager',
                'Certified Public Accountant'
            ],
            'Healthcare': [
                'RHIA', 'RHIT', 'CCS', 'CHPS', 'HIMSS', 'Healthcare Information'
            ]
        }
        
        # Date patterns for certification dates
        date_patterns = [
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(19|20)\d{2}\b'
        ]
        
        # Expiration patterns
        expiration_patterns = [
            r'expires?\s*:?\s*([^,\n]+)',
            r'valid\s+until\s*:?\s*([^,\n]+)',
            r'expiration\s*:?\s*([^,\n]+)'
        ]
        
        lines = cert_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Check each certification pattern
            for provider, cert_list in cert_patterns.items():
                for cert_name in cert_list:
                    # Case-insensitive search for certification name
                    if re.search(re.escape(cert_name), line, re.IGNORECASE):
                        certification = {
                            'name': cert_name,
                            'issuing_organization': provider,
                            'description': line.strip()
                        }
                        
                        # Extract issue date
                        for date_pattern in date_patterns:
                            date_match = re.search(date_pattern, line, re.IGNORECASE)
                            if date_match:
                                try:
                                    date_str = date_match.group(0)
                                    # Try to parse and format the date
                                    if re.match(r'\b(19|20)\d{2}\b', date_str):
                                        certification['issue_date'] = f"{date_str}-01-01"
                                    else:
                                        # For more complex date parsing, you might want to use dateutil
                                        certification['issue_date'] = date_str
                                except:
                                    pass
                                break
                        
                        # Extract expiration date
                        for exp_pattern in expiration_patterns:
                            exp_match = re.search(exp_pattern, line, re.IGNORECASE)
                            if exp_match:
                                certification['expiration_date'] = exp_match.group(1).strip()
                                break
                        
                        # Extract credential ID if present
                        credential_patterns = [
                            r'(?:ID|credential|certificate)\s*:?\s*([A-Z0-9-]+)',
                            r'([A-Z0-9]{6,})'  # Generic alphanumeric ID
                        ]
                        
                        for cred_pattern in credential_patterns:
                            cred_match = re.search(cred_pattern, line)
                            if cred_match:
                                certification['credential_id'] = cred_match.group(1)
                                break
                        
                        # Check if we already have this certification
                        if not any(cert['name'] == cert_name for cert in certifications):
                            certifications.append(certification)
                        break
        
        # Additional pattern matching for generic certifications
        generic_cert_patterns = [
            r'Certified\s+([A-Z][A-Za-z\s]+?)(?:\s*[-–]\s*|\s*,|\s*\n)',
            r'([A-Z][A-Za-z\s]+?)\s+Certification',
            r'([A-Z][A-Za-z\s]+?)\s+Certificate'
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in generic_cert_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    cert_name = match.strip()
                    if len(cert_name) > 3 and len(cert_name) < 100:
                        # Check if it's not already captured
                        if not any(cert['name'].lower() == cert_name.lower() for cert in certifications):
                            certification = {
                                'name': cert_name,
                                'issuing_organization': 'Unknown',
                                'description': line.strip()
                            }
                            
                            # Try to extract date
                            for date_pattern in date_patterns:
                                date_match = re.search(date_pattern, line)
                                if date_match:
                                    certification['issue_date'] = date_match.group(0)
                                    break
                            
                            certifications.append(certification)
        
        return certifications
    
    def _extract_section(self, text: str, keywords: List[str]) -> str:
        """Extract a specific section from CV text based on keywords"""
        lines = text.split('\n')
        section_start = -1
        section_end = len(lines)
        
        # Find section start
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in keywords):
                # Check if this looks like a section header
                if len(line.strip()) < 50 and (line.isupper() or line.istitle()):
                    section_start = i + 1
                    break
        
        if section_start == -1:
            return ""
        
        # Find section end (next section header or end of document)
        common_sections = [
            'education', 'experience', 'skills', 'projects', 'certifications',
            'awards', 'publications', 'references', 'interests', 'hobbies'
        ]
        
        for i in range(section_start, len(lines)):
            line = lines[i].strip().lower()
            if line and len(line) < 50:
                if any(section in line for section in common_sections):
                    if not any(keyword in line for keyword in keywords):
                        section_end = i
                        break
        
        return '\n'.join(lines[section_start:section_end])
    
    async def parse_cv(self, file_path: str, user_id: str) -> ParsedData:
        """Parse CV and extract all structured data"""
        try:
            # Extract raw text
            raw_text = await self.extract_text_from_pdf(file_path, user_id)
            
            # Parse different sections
            personal_info = self.parse_personal_info(raw_text)
            education = self.parse_education(raw_text)
            experience = self.parse_experience(raw_text)
            skills = self.parse_skills(raw_text)
            
            # Extract profile information
            profile = {}
            
            # Look for summary/objective section
            summary_section = self._extract_section(raw_text, ['summary', 'objective', 'profile', 'about'])
            if summary_section:
                # Take first few sentences as summary
                sentences = summary_section.split('.')[:3]
                profile['summary'] = '. '.join(sentences).strip()
                if profile['summary'] and not profile['summary'].endswith('.'):
                    profile['summary'] += '.'
            
            # Parse certifications
            certifications = self.parse_certifications(raw_text)
            
            return ParsedData(
                personal_info=personal_info if personal_info else None,
                profile=profile if profile else None,
                education=education if education else None,
                experience=experience if experience else None,
                skills=skills if skills else None,
                certifications=certifications if certifications else None,
                raw_text=raw_text
            )
            
        except Exception as e:
            raise Exception(f"Failed to parse CV: {str(e)}")