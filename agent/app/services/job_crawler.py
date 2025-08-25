"""
Job crawling service using hybrid LLM strategy
"""

import asyncio
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from supabase import Client

from app.models.jobs import (
    JobSiteWatchlist,
    JobCreate,
    WorkMode,
    JobType,
    CrawlingLogCreate,
    CrawlingStatus,
)
from app.services.job_watchlist import JobWatchlistService
from app.core.config import settings


class JobCrawlerService:
    """Service for crawling job sites and extracting job data"""
    
    def __init__(self, db: Client):
        self.db = db
        self.watchlist_service = JobWatchlistService(db)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    async def crawl_all_active_sites(self) -> Dict[str, Any]:
        """Crawl all active job sites for all users"""
        results = {
            "sites_processed": 0,
            "total_jobs_found": 0,
            "total_jobs_new": 0,
            "errors": []
        }
        
        # Get all active watchlist sites
        active_sites_result = self.db.table("job_sites_watchlist").select("*").eq("is_active", True).execute()
        
        for site_data in active_sites_result.data:
            site = JobSiteWatchlist(**site_data)
            try:
                crawl_result = await self.crawl_site(site)
                results["sites_processed"] += 1
                results["total_jobs_found"] += crawl_result["jobs_found"]
                results["total_jobs_new"] += crawl_result["jobs_new"]
            except Exception as e:
                results["errors"].append({
                    "site_id": site.id,
                    "site_url": str(site.site_url),
                    "error": str(e)
                })
        
        return results
    
    async def crawl_site(self, site: JobSiteWatchlist) -> Dict[str, Any]:
        """Crawl a specific job site"""
        start_time = datetime.utcnow()
        
        # Create crawling log
        log_data = CrawlingLogCreate(
            site_id=site.id,
            status=CrawlingStatus.STARTED
        )
        crawling_log = await self.watchlist_service.create_crawling_log(log_data)
        
        try:
            # Determine crawling strategy based on site
            jobs_data = await self._crawl_site_jobs(site)
            
            # Process and store jobs
            jobs_new = 0
            jobs_updated = 0
            
            for job_data in jobs_data:
                try:
                    job_create = JobCreate(
                        site_id=site.id,
                        external_id=job_data.get("external_id"),
                        title=job_data["title"],
                        company=job_data.get("company"),
                        location=job_data.get("location"),
                        work_mode=self._parse_work_mode(job_data.get("work_mode")),
                        job_type=self._parse_job_type(job_data.get("job_type")),
                        description=job_data.get("description"),
                        requirements=job_data.get("requirements"),
                        compensation=job_data.get("compensation"),
                        job_url=job_data.get("job_url"),
                        posted_date=self._parse_date(job_data.get("posted_date")),
                        expires_at=self._parse_date(job_data.get("expires_at")),
                        raw_data=job_data
                    )
                    
                    # Check if job already exists
                    existing_job = None
                    if job_create.external_id:
                        existing_result = self.db.table("jobs").select("id").eq("site_id", site.id).eq("external_id", job_create.external_id).execute()
                        if existing_result.data:
                            existing_job = existing_result.data[0]
                    
                    if existing_job:
                        jobs_updated += 1
                    else:
                        jobs_new += 1
                    
                    await self.watchlist_service.upsert_job(job_create)
                    
                except Exception as e:
                    print(f"Error processing job: {e}")
                    continue
            
            # Update crawling log with success
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self.watchlist_service.update_crawling_log(
                crawling_log.id,
                CrawlingStatus.COMPLETED.value,
                jobs_found=len(jobs_data),
                jobs_new=jobs_new,
                jobs_updated=jobs_updated,
                execution_time_ms=execution_time
            )
            
            # Update site's last crawled timestamp
            await self.watchlist_service.update_last_crawled(site.id)
            
            return {
                "jobs_found": len(jobs_data),
                "jobs_new": jobs_new,
                "jobs_updated": jobs_updated,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            # Update crawling log with error
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self.watchlist_service.update_crawling_log(
                crawling_log.id,
                CrawlingStatus.FAILED.value,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            raise e
    
    async def _crawl_site_jobs(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Crawl jobs from a specific site using appropriate strategy"""
        site_url = str(site.site_url)
        domain = urlparse(site_url).netloc.lower()
        
        # Strategy 1: Try known job board patterns
        if any(known_site in domain for known_site in ['indeed.com', 'glassdoor.com', 'linkedin.com']):
            return await self._crawl_known_job_board(site)
        
        # Strategy 2: Generic HTML scraping
        return await self._crawl_generic_site(site)
    
    async def _crawl_known_job_board(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Crawl known job boards with specific patterns"""
        site_url = str(site.site_url)
        domain = urlparse(site_url).netloc.lower()
        
        if 'indeed.com' in domain:
            return await self._crawl_indeed(site)
        elif 'glassdoor.com' in domain:
            return await self._crawl_glassdoor(site)
        elif 'linkedin.com' in domain:
            return await self._crawl_linkedin(site)
        
        return []
    
    async def _crawl_indeed(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Crawl Indeed job listings"""
        jobs = []
        
        try:
            # Build search URL with filters
            base_url = str(site.site_url)
            params = self._build_indeed_params(site.filters)
            
            response = self.session.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job cards (Indeed's structure)
            job_cards = soup.find_all('div', {'data-jk': True}) or soup.find_all('a', {'data-jk': True})
            
            for card in job_cards[:20]:  # Limit to 20 jobs per crawl
                try:
                    job_data = self._extract_indeed_job_data(card, base_url)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    print(f"Error extracting Indeed job: {e}")
                    continue
            
        except Exception as e:
            print(f"Error crawling Indeed: {e}")
        
        return jobs
    
    async def _crawl_glassdoor(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Crawl Glassdoor job listings"""
        jobs = []
        
        try:
            response = self.session.get(str(site.site_url), timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Glassdoor job cards
            job_cards = soup.find_all('div', class_=re.compile(r'job.*card|JobCard'))
            
            for card in job_cards[:20]:
                try:
                    job_data = self._extract_glassdoor_job_data(card, str(site.site_url))
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    print(f"Error extracting Glassdoor job: {e}")
                    continue
            
        except Exception as e:
            print(f"Error crawling Glassdoor: {e}")
        
        return jobs
    
    async def _crawl_linkedin(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Crawl LinkedIn job listings"""
        jobs = []
        
        try:
            response = self.session.get(str(site.site_url), timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # LinkedIn job cards
            job_cards = soup.find_all('div', class_=re.compile(r'job.*card|base-card'))
            
            for card in job_cards[:20]:
                try:
                    job_data = self._extract_linkedin_job_data(card, str(site.site_url))
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    print(f"Error extracting LinkedIn job: {e}")
                    continue
            
        except Exception as e:
            print(f"Error crawling LinkedIn: {e}")
        
        return jobs
    
    async def _crawl_generic_site(self, site: JobSiteWatchlist) -> List[Dict[str, Any]]:
        """Generic site crawling using common patterns"""
        jobs = []
        
        try:
            response = self.session.get(str(site.site_url), timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for common job listing patterns
            job_selectors = [
                'div[class*="job"]',
                'article[class*="job"]',
                'li[class*="job"]',
                '.job-listing',
                '.job-card',
                '.position',
                '.vacancy'
            ]
            
            job_elements = []
            for selector in job_selectors:
                elements = soup.select(selector)
                if elements:
                    job_elements = elements[:20]  # Take first 20
                    break
            
            for element in job_elements:
                try:
                    job_data = self._extract_generic_job_data(element, str(site.site_url))
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    print(f"Error extracting generic job: {e}")
                    continue
            
        except Exception as e:
            print(f"Error crawling generic site: {e}")
        
        return jobs
    
    def _build_indeed_params(self, filters) -> Dict[str, str]:
        """Build Indeed search parameters from filters"""
        params = {}
        
        if filters.keywords:
            params['q'] = ' '.join(filters.keywords)
        if filters.location:
            params['l'] = filters.location
        if filters.work_mode == WorkMode.REMOTE:
            params['remotejob'] = '1'
        if filters.job_type:
            type_map = {
                JobType.FULL_TIME: 'fulltime',
                JobType.PART_TIME: 'parttime',
                JobType.CONTRACT: 'contract',
                JobType.INTERNSHIP: 'internship'
            }
            params['jt'] = type_map.get(filters.job_type, '')
        
        return params
    
    def _extract_indeed_job_data(self, card, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from Indeed job card"""
        try:
            # Job ID
            external_id = card.get('data-jk') or card.get('id', '')
            
            # Title
            title_elem = card.find('h2') or card.find('a', {'data-jk': True})
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Company
            company_elem = card.find('span', class_=re.compile(r'company'))
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            # Location
            location_elem = card.find('div', {'data-testid': 'job-location'}) or card.find('span', class_=re.compile(r'location'))
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            # Job URL
            link_elem = card.find('a', href=True)
            job_url = urljoin(base_url, link_elem['href']) if link_elem else ''
            
            # Description snippet
            description_elem = card.find('div', class_=re.compile(r'summary|snippet'))
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            if not title:
                return None
            
            return {
                'external_id': external_id,
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'job_url': job_url,
                'posted_date': datetime.utcnow().isoformat(),
                'source': 'indeed'
            }
            
        except Exception as e:
            print(f"Error extracting Indeed job data: {e}")
            return None
    
    def _extract_glassdoor_job_data(self, card, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from Glassdoor job card"""
        try:
            # Similar extraction logic for Glassdoor
            title_elem = card.find('a', class_=re.compile(r'job.*title'))
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            company_elem = card.find('span', class_=re.compile(r'employer'))
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            location_elem = card.find('span', class_=re.compile(r'location'))
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            if not title:
                return None
            
            return {
                'external_id': f"glassdoor_{hash(title + company)}",
                'title': title,
                'company': company,
                'location': location,
                'posted_date': datetime.utcnow().isoformat(),
                'source': 'glassdoor'
            }
            
        except Exception as e:
            print(f"Error extracting Glassdoor job data: {e}")
            return None
    
    def _extract_linkedin_job_data(self, card, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from LinkedIn job card"""
        try:
            # LinkedIn extraction logic
            title_elem = card.find('h3') or card.find('a', class_=re.compile(r'job.*title'))
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            company_elem = card.find('h4') or card.find('span', class_=re.compile(r'company'))
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            location_elem = card.find('span', class_=re.compile(r'location'))
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            if not title:
                return None
            
            return {
                'external_id': f"linkedin_{hash(title + company)}",
                'title': title,
                'company': company,
                'location': location,
                'posted_date': datetime.utcnow().isoformat(),
                'source': 'linkedin'
            }
            
        except Exception as e:
            print(f"Error extracting LinkedIn job data: {e}")
            return None
    
    def _extract_generic_job_data(self, element, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from generic job listing element"""
        try:
            # Generic extraction using common patterns
            text_content = element.get_text(strip=True)
            
            # Try to find title (usually in h1-h6 or first link)
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find('a')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Try to find company name
            company = ''
            company_patterns = [r'at\s+([A-Z][^,\n]+)', r'Company:\s*([^,\n]+)', r'Employer:\s*([^,\n]+)']
            for pattern in company_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    company = match.group(1).strip()
                    break
            
            # Try to find location
            location = ''
            location_patterns = [r'Location:\s*([^,\n]+)', r'([A-Z][a-z]+,\s*[A-Z]{2})', r'Remote', r'Hybrid']
            for pattern in location_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    location = match.group(1).strip() if match.groups() else match.group(0)
                    break
            
            # Get job URL
            link_elem = element.find('a', href=True)
            job_url = urljoin(base_url, link_elem['href']) if link_elem else ''
            
            if not title or len(title) < 3:
                return None
            
            return {
                'external_id': f"generic_{hash(title + company + location)}",
                'title': title,
                'company': company,
                'location': location,
                'description': text_content[:500],  # First 500 chars
                'job_url': job_url,
                'posted_date': datetime.utcnow().isoformat(),
                'source': 'generic'
            }
            
        except Exception as e:
            print(f"Error extracting generic job data: {e}")
            return None
    
    def _parse_work_mode(self, work_mode_str: Optional[str]) -> Optional[WorkMode]:
        """Parse work mode from string"""
        if not work_mode_str:
            return None
        
        work_mode_str = work_mode_str.lower()
        if 'remote' in work_mode_str:
            return WorkMode.REMOTE
        elif 'hybrid' in work_mode_str:
            return WorkMode.HYBRID
        elif 'onsite' in work_mode_str or 'office' in work_mode_str:
            return WorkMode.ONSITE
        
        return None
    
    def _parse_job_type(self, job_type_str: Optional[str]) -> Optional[JobType]:
        """Parse job type from string"""
        if not job_type_str:
            return None
        
        job_type_str = job_type_str.lower()
        if 'full' in job_type_str and 'time' in job_type_str:
            return JobType.FULL_TIME
        elif 'part' in job_type_str and 'time' in job_type_str:
            return JobType.PART_TIME
        elif 'contract' in job_type_str or 'freelance' in job_type_str:
            return JobType.CONTRACT
        elif 'intern' in job_type_str:
            return JobType.INTERNSHIP
        
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date from various string formats"""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Handle relative dates like "2 days ago"
            if 'ago' in date_str.lower():
                if 'day' in date_str:
                    days = int(re.search(r'(\d+)', date_str).group(1))
                    return datetime.utcnow() - timedelta(days=days)
                elif 'hour' in date_str:
                    hours = int(re.search(r'(\d+)', date_str).group(1))
                    return datetime.utcnow() - timedelta(hours=hours)
            
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
        
        return None