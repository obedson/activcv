"""
Background job service for automated crawling and matching
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from supabase import Client

from app.core.database import Database
from app.services.job_crawler import JobCrawlerService
from app.services.job_matcher import JobMatcherService
from app.core.config import settings


class BackgroundJobService:
    """Service for running background jobs like crawling and matching"""
    
    def __init__(self):
        self.db = Database.get_service_client()
        self.crawler_service = JobCrawlerService(self.db)
        self.matcher_service = JobMatcherService(self.db)
        self.is_running = False
    
    def start_scheduler(self):
        """Start the background job scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Schedule daily crawling at 6 AM
        schedule.every().day.at("06:00").do(self._run_daily_crawling)
        
        # Schedule job matching every 4 hours
        schedule.every(4).hours.do(self._run_job_matching)
        
        # Schedule cleanup every week
        schedule.every().week.do(self._run_cleanup)
        
        print("Background job scheduler started")
        
        # Run scheduler loop
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the background job scheduler"""
        self.is_running = False
        schedule.clear()
        print("Background job scheduler stopped")
    
    async def _run_daily_crawling(self):
        """Run daily crawling for all active sites"""
        print(f"Starting daily crawling at {datetime.utcnow()}")
        
        try:
            results = await self.crawler_service.crawl_all_active_sites()
            
            print(f"Daily crawling completed:")
            print(f"  - Sites processed: {results['sites_processed']}")
            print(f"  - Total jobs found: {results['total_jobs_found']}")
            print(f"  - New jobs: {results['total_jobs_new']}")
            print(f"  - Errors: {len(results['errors'])}")
            
            if results['errors']:
                for error in results['errors']:
                    print(f"  - Error for {error['site_url']}: {error['error']}")
            
            # Log crawling summary
            await self._log_crawling_summary(results)
            
        except Exception as e:
            print(f"Error in daily crawling: {e}")
    
    async def _run_job_matching(self):
        """Run job matching for all users"""
        print(f"Starting job matching at {datetime.utcnow()}")
        
        try:
            results = await self.matcher_service.match_all_users()
            
            print(f"Job matching completed:")
            print(f"  - Users processed: {results['users_processed']}")
            print(f"  - Suggestions created: {results['suggestions_created']}")
            print(f"  - Errors: {len(results['errors'])}")
            
            if results['errors']:
                for error in results['errors']:
                    print(f"  - Error for user {error['user_id']}: {error['error']}")
            
        except Exception as e:
            print(f"Error in job matching: {e}")
    
    async def _run_cleanup(self):
        """Run weekly cleanup tasks"""
        print(f"Starting weekly cleanup at {datetime.utcnow()}")
        
        try:
            # Clean up old jobs (older than 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            old_jobs_result = self.db.table("jobs").delete().lt("created_at", cutoff_date.isoformat()).execute()
            deleted_jobs = len(old_jobs_result.data) if old_jobs_result.data else 0
            
            # Clean up old crawling logs (older than 90 days)
            log_cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            old_logs_result = self.db.table("crawling_logs").delete().lt("started_at", log_cutoff_date.isoformat()).execute()
            deleted_logs = len(old_logs_result.data) if old_logs_result.data else 0
            
            # Clean up dismissed suggestions (older than 7 days)
            suggestion_cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            old_suggestions_result = self.db.table("suggested_jobs").delete().eq("is_dismissed", True).lt("created_at", suggestion_cutoff_date.isoformat()).execute()
            deleted_suggestions = len(old_suggestions_result.data) if old_suggestions_result.data else 0
            
            print(f"Weekly cleanup completed:")
            print(f"  - Old jobs deleted: {deleted_jobs}")
            print(f"  - Old logs deleted: {deleted_logs}")
            print(f"  - Old dismissed suggestions deleted: {deleted_suggestions}")
            
        except Exception as e:
            print(f"Error in weekly cleanup: {e}")
    
    async def _log_crawling_summary(self, results: Dict[str, Any]):
        """Log crawling summary to database"""
        try:
            summary_data = {
                "event_type": "daily_crawling_summary",
                "sites_processed": results["sites_processed"],
                "total_jobs_found": results["total_jobs_found"],
                "total_jobs_new": results["total_jobs_new"],
                "errors_count": len(results["errors"]),
                "errors": results["errors"][:10],  # Limit to first 10 errors
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in a system logs table (would need to create this table)
            # For now, just print the summary
            print(f"Crawling summary logged: {summary_data}")
            
        except Exception as e:
            print(f"Error logging crawling summary: {e}")
    
    async def run_manual_crawling(self, site_id: str = None) -> Dict[str, Any]:
        """Run manual crawling for a specific site or all sites"""
        if site_id:
            # Get specific site
            site_result = self.db.table("job_sites_watchlist").select("*").eq("id", site_id).execute()
            if not site_result.data:
                return {"error": "Site not found"}
            
            from app.models.jobs import JobSiteWatchlist
            site = JobSiteWatchlist(**site_result.data[0])
            
            try:
                result = await self.crawler_service.crawl_site(site)
                return {
                    "success": True,
                    "site_id": site_id,
                    "jobs_found": result["jobs_found"],
                    "jobs_new": result["jobs_new"],
                    "execution_time_ms": result["execution_time_ms"]
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            # Run for all sites
            return await self.crawler_service.crawl_all_active_sites()
    
    async def run_manual_matching(self, user_id: str = None) -> Dict[str, Any]:
        """Run manual job matching for a specific user or all users"""
        if user_id:
            try:
                suggestions = await self.matcher_service.match_jobs_for_user(user_id)
                
                # Create suggestions in database
                created_count = 0
                for suggestion in suggestions:
                    try:
                        from app.services.job_watchlist import JobWatchlistService
                        watchlist_service = JobWatchlistService(self.db)
                        await watchlist_service.create_suggested_job(suggestion)
                        created_count += 1
                    except Exception as e:
                        # Might fail due to duplicate constraint
                        if "duplicate" not in str(e).lower():
                            print(f"Error creating suggestion: {e}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "suggestions_found": len(suggestions),
                    "suggestions_created": created_count
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            # Run for all users
            return await self.matcher_service.match_all_users()


# Global instance for the background service
background_service = BackgroundJobService()


def start_background_jobs():
    """Start background jobs (call this from main application)"""
    import threading
    
    def run_scheduler():
        asyncio.set_event_loop(asyncio.new_event_loop())
        background_service.start_scheduler()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background jobs started in separate thread")


def stop_background_jobs():
    """Stop background jobs"""
    background_service.stop_scheduler()


# CLI commands for manual execution
async def run_crawling_command(site_id: str = None):
    """CLI command to run crawling"""
    result = await background_service.run_manual_crawling(site_id)
    print(f"Crawling result: {result}")


async def run_matching_command(user_id: str = None):
    """CLI command to run job matching"""
    result = await background_service.run_manual_matching(user_id)
    print(f"Matching result: {result}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "crawl":
            site_id = sys.argv[2] if len(sys.argv) > 2 else None
            asyncio.run(run_crawling_command(site_id))
        elif command == "match":
            user_id = sys.argv[2] if len(sys.argv) > 2 else None
            asyncio.run(run_matching_command(user_id))
        else:
            print("Usage: python background_jobs.py [crawl|match] [site_id|user_id]")
    else:
        # Start the scheduler
        background_service.start_scheduler()