#!/usr/bin/env python3
"""
CLI script for AI CV Agent background operations
"""

import asyncio
import sys
import argparse
from app.services.background_jobs import BackgroundJobService


async def main():
    parser = argparse.ArgumentParser(description='AI CV Agent CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Run job site crawling')
    crawl_parser.add_argument('--site-id', help='Specific site ID to crawl (optional)')
    
    # Match command
    match_parser = subparsers.add_parser('match', help='Run job matching')
    match_parser.add_argument('--user-id', help='Specific user ID to match (optional)')
    
    # Scheduler command
    scheduler_parser = subparsers.add_parser('scheduler', help='Start background job scheduler')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show system statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    background_service = BackgroundJobService()
    
    if args.command == 'crawl':
        print("Starting job crawling...")
        result = await background_service.run_manual_crawling(args.site_id)
        print(f"Crawling completed: {result}")
    
    elif args.command == 'match':
        print("Starting job matching...")
        result = await background_service.run_manual_matching(args.user_id)
        print(f"Matching completed: {result}")
    
    elif args.command == 'scheduler':
        print("Starting background job scheduler...")
        print("Press Ctrl+C to stop")
        try:
            background_service.start_scheduler()
        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            background_service.stop_scheduler()
    
    elif args.command == 'stats':
        print("System Statistics:")
        print("==================")
        
        # Get basic stats from database
        db = background_service.db
        
        # Count watchlist sites
        watchlist_result = db.table("job_sites_watchlist").select("id", count="exact").execute()
        print(f"Total watchlist sites: {watchlist_result.count or 0}")
        
        # Count active sites
        active_sites_result = db.table("job_sites_watchlist").select("id", count="exact").eq("is_active", True).execute()
        print(f"Active watchlist sites: {active_sites_result.count or 0}")
        
        # Count total jobs
        jobs_result = db.table("jobs").select("id", count="exact").execute()
        print(f"Total jobs found: {jobs_result.count or 0}")
        
        # Count suggested jobs
        suggestions_result = db.table("suggested_jobs").select("id", count="exact").execute()
        print(f"Total job suggestions: {suggestions_result.count or 0}")
        
        # Count generated CVs
        cvs_result = db.table("generated_cvs").select("id", count="exact").execute()
        print(f"Total generated CVs: {cvs_result.count or 0}")
        
        # Recent crawling activity
        recent_logs_result = db.table("crawling_logs").select("*").order("started_at", desc=True).limit(5).execute()
        if recent_logs_result.data:
            print(f"\nRecent crawling activity:")
            for log in recent_logs_result.data:
                print(f"  - {log['started_at']}: {log['status']} ({log.get('jobs_found', 0)} jobs)")


if __name__ == "__main__":
    asyncio.run(main())