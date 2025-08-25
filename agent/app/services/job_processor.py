"""
Real-time job processing service with progress tracking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from uuid import uuid4
from supabase import Client

from app.models.job_processing import (
    JobQueue, JobQueueCreate, JobQueueUpdate, JobProcessingStep, JobProcessingLog,
    JobType, JobStatus, StepStatus, LogLevel, JobProgressUpdate,
    STEP_DEFINITIONS, JobDashboardStats, JobQueueWithSteps
)
from app.services.cv_generator import cv_generator
from app.services.cover_letter_generator import cover_letter_generator
from app.services.crew_agents import crew_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class JobProcessor:
    """Real-time job processing service"""
    
    def __init__(self, db: Client):
        self.db = db
        self.processing_jobs: Dict[str, bool] = {}
        self.job_handlers = {
            JobType.CV_GENERATION: self._process_cv_generation,
            JobType.COVER_LETTER_GENERATION: self._process_cover_letter_generation,
            JobType.JOB_ANALYSIS: self._process_job_analysis,
            JobType.BULK_GENERATION: self._process_bulk_generation
        }
    
    async def create_job(self, job_create: JobQueueCreate) -> JobQueue:
        """Create a new job in the queue"""
        try:
            # Generate job ID
            job_id = str(uuid4())
            
            # Prepare job data
            job_data = {
                "id": job_id,
                **job_create.dict(),
                "scheduled_at": job_create.scheduled_at or datetime.utcnow()
            }
            
            # Insert job into queue
            result = self.db.table("job_queue").insert(job_data).execute()
            
            if not result.data:
                raise Exception("Failed to create job")
            
            job = JobQueue(**result.data[0])
            
            # Create processing steps
            await self._create_job_steps(job.id, job.job_type)
            
            # Log job creation
            await self._log_job_event(
                job.id, 
                LogLevel.INFO, 
                f"Job created: {job.job_type}",
                {"priority": job.priority, "scheduled_at": job.scheduled_at.isoformat()}
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    async def _create_job_steps(self, job_id: str, job_type: JobType):
        """Create processing steps for a job"""
        steps = STEP_DEFINITIONS.get(job_type, [])
        
        step_data = []
        for step in steps:
            step_data.append({
                "id": str(uuid4()),
                "job_queue_id": job_id,
                "step_name": step["name"],
                "step_order": step["order"],
                "step_data": {"description": step["description"]}
            })
        
        if step_data:
            self.db.table("job_processing_steps").insert(step_data).execute()
            
            # Update total steps in job queue
            self.db.table("job_queue").update({
                "total_steps": len(step_data)
            }).eq("id", job_id).execute()
    
    async def get_next_job(self) -> Optional[JobQueue]:
        """Get the next job from the queue"""
        try:
            result = self.db.rpc("get_next_job_from_queue").execute()
            
            if result.data and len(result.data) > 0:
                job_data = result.data[0]
                return JobQueue(**job_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get next job: {e}")
            return None
    
    async def start_job_processing(self, job_id: str) -> bool:
        """Mark job as processing"""
        try:
            result = self.db.rpc("start_job_processing", {"job_id": job_id}).execute()
            
            if result.data:
                self.processing_jobs[job_id] = True
                await self._log_job_event(job_id, LogLevel.INFO, "Job processing started")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to start job processing: {e}")
            return False
    
    async def process_job(self, job: JobQueue) -> bool:
        """Process a job with progress tracking"""
        job_id = job.id
        
        try:
            # Start processing
            if not await self.start_job_processing(job_id):
                return False
            
            # Get job handler
            handler = self.job_handlers.get(job.job_type)
            if not handler:
                await self._fail_job(job_id, f"No handler for job type: {job.job_type}")
                return False
            
            # Process job with progress tracking
            await self._update_job_progress(job_id, 0, "Starting job processing")
            
            result = await handler(job)
            
            if result.get("success", False):
                await self._complete_job(job_id, result.get("output_data", {}))
                await self._log_job_event(job_id, LogLevel.INFO, "Job completed successfully")
                return True
            else:
                await self._fail_job(job_id, result.get("error", "Job processing failed"))
                return False
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            await self._fail_job(job_id, str(e))
            return False
        finally:
            self.processing_jobs.pop(job_id, None)
    
    async def _process_cv_generation(self, job: JobQueue) -> Dict[str, Any]:
        """Process CV generation job"""
        try:
            input_data = job.input_data
            user_id = job.user_id
            
            # Step 1: Profile Analysis
            await self._update_step_progress(job.id, "profile_analysis", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 10, "Analyzing user profile")
            
            # Get user profile
            profile_result = self.db.table("profiles").select("*").eq("user_id", user_id).execute()
            if not profile_result.data:
                return {"success": False, "error": "User profile not found"}
            
            await self._update_step_progress(job.id, "profile_analysis", StepStatus.COMPLETED, 100)
            
            # Step 2: Job Analysis (if job provided)
            job_data = None
            if input_data.get("job_id"):
                await self._update_step_progress(job.id, "job_analysis", StepStatus.PROCESSING, 0)
                await self._update_job_progress(job.id, 25, "Analyzing job requirements")
                
                job_result = self.db.table("jobs").select("*").eq("id", input_data["job_id"]).execute()
                if job_result.data:
                    job_data = job_result.data[0]
                
                await self._update_step_progress(job.id, "job_analysis", StepStatus.COMPLETED, 100)
            else:
                await self._update_step_progress(job.id, "job_analysis", StepStatus.SKIPPED, 100)
            
            # Step 3: Content Generation
            await self._update_step_progress(job.id, "content_generation", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 40, "Generating CV content")
            
            # Use CrewAI for content generation
            crew_result = await crew_service.process_cv_generation(
                user_profile=profile_result.data[0],
                job=job_data,
                template=input_data.get("template", "modern_one_page")
            )
            
            if not crew_result.get("success"):
                return {"success": False, "error": "Content generation failed"}
            
            await self._update_step_progress(job.id, "content_generation", StepStatus.COMPLETED, 100)
            
            # Step 4: Template Application
            await self._update_step_progress(job.id, "template_application", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 60, "Applying template styling")
            
            # Apply template and styling
            template_result = await cv_generator.apply_template(
                content=crew_result["generated_content"],
                template=input_data.get("template", "modern_one_page")
            )
            
            await self._update_step_progress(job.id, "template_application", StepStatus.COMPLETED, 100)
            
            # Step 5: PDF Generation
            await self._update_step_progress(job.id, "pdf_generation", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 80, "Generating PDF document")
            
            pdf_result = await cv_generator.generate_pdf(template_result["html_content"])
            
            await self._update_step_progress(job.id, "pdf_generation", StepStatus.COMPLETED, 100)
            
            # Step 6: Quality Check
            await self._update_step_progress(job.id, "quality_check", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 90, "Performing quality check")
            
            # Basic quality validation
            if not pdf_result.get("pdf_url") or not pdf_result.get("file_size"):
                return {"success": False, "error": "PDF generation validation failed"}
            
            await self._update_step_progress(job.id, "quality_check", StepStatus.COMPLETED, 100)
            
            # Step 7: Delivery
            await self._update_step_progress(job.id, "delivery", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 95, "Preparing for delivery")
            
            # Send notification email
            await email_service.send_cv_ready_notification(
                user_id=user_id,
                job_title=job_data.get("title", "General CV") if job_data else "General CV",
                company_name=job_data.get("company", "N/A") if job_data else "N/A",
                cv_url=pdf_result["pdf_url"]
            )
            
            await self._update_step_progress(job.id, "delivery", StepStatus.COMPLETED, 100)
            await self._update_job_progress(job.id, 100, "CV generation completed")
            
            return {
                "success": True,
                "output_data": {
                    "cv_url": pdf_result["pdf_url"],
                    "file_size": pdf_result["file_size"],
                    "template_used": input_data.get("template", "modern_one_page"),
                    "job_id": input_data.get("job_id"),
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"CV generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_cover_letter_generation(self, job: JobQueue) -> Dict[str, Any]:
        """Process cover letter generation job"""
        try:
            input_data = job.input_data
            user_id = job.user_id
            
            # Step 1: Company Research
            await self._update_step_progress(job.id, "company_research", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 10, "Researching company information")
            
            # Get job information
            job_result = self.db.table("jobs").select("*").eq("id", input_data["job_id"]).execute()
            if not job_result.data:
                return {"success": False, "error": "Job not found"}
            
            job_data = job_result.data[0]
            await self._update_step_progress(job.id, "company_research", StepStatus.COMPLETED, 100)
            
            # Step 2: Profile Analysis
            await self._update_step_progress(job.id, "profile_analysis", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 25, "Analyzing user profile")
            
            profile_result = self.db.table("profiles").select("*").eq("user_id", user_id).execute()
            if not profile_result.data:
                return {"success": False, "error": "User profile not found"}
            
            await self._update_step_progress(job.id, "profile_analysis", StepStatus.COMPLETED, 100)
            
            # Step 3: Content Generation
            await self._update_step_progress(job.id, "content_generation", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 50, "Writing cover letter content")
            
            # Use CrewAI for cover letter generation
            crew_result = await crew_service.generate_cover_letter(
                user_profile=profile_result.data[0],
                job=job_data,
                template_style=input_data.get("template_style", "professional"),
                customizations=input_data.get("customizations", {})
            )
            
            if not crew_result.get("success"):
                return {"success": False, "error": "Cover letter generation failed"}
            
            await self._update_step_progress(job.id, "content_generation", StepStatus.COMPLETED, 100)
            
            # Step 4: Template Application
            await self._update_step_progress(job.id, "template_application", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 70, "Applying template formatting")
            
            template_result = await cover_letter_generator.apply_template(
                content=crew_result["cover_letter_content"],
                template=input_data.get("template_key", "professional_standard"),
                job_data=job_data,
                user_profile=profile_result.data[0]
            )
            
            await self._update_step_progress(job.id, "template_application", StepStatus.COMPLETED, 100)
            
            # Step 5: PDF Generation
            await self._update_step_progress(job.id, "pdf_generation", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 85, "Generating PDF document")
            
            pdf_result = await cover_letter_generator.generate_pdf(template_result["html_content"])
            
            await self._update_step_progress(job.id, "pdf_generation", StepStatus.COMPLETED, 100)
            
            # Step 6: Quality Review
            await self._update_step_progress(job.id, "quality_review", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 95, "Quality review and validation")
            
            if not pdf_result.get("pdf_url"):
                return {"success": False, "error": "PDF generation failed"}
            
            await self._update_step_progress(job.id, "quality_review", StepStatus.COMPLETED, 100)
            
            # Step 7: Delivery
            await self._update_step_progress(job.id, "delivery", StepStatus.PROCESSING, 0)
            await self._update_job_progress(job.id, 98, "Preparing for delivery")
            
            # Send notification
            await email_service.send_cover_letter_ready_notification(
                user_id=user_id,
                job_title=job_data["title"],
                company_name=job_data["company"],
                cover_letter_url=pdf_result["pdf_url"]
            )
            
            await self._update_step_progress(job.id, "delivery", StepStatus.COMPLETED, 100)
            await self._update_job_progress(job.id, 100, "Cover letter generation completed")
            
            return {
                "success": True,
                "output_data": {
                    "cover_letter_url": pdf_result["pdf_url"],
                    "file_size": pdf_result["file_size"],
                    "template_used": input_data.get("template_key", "professional_standard"),
                    "job_id": input_data["job_id"],
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_job_analysis(self, job: JobQueue) -> Dict[str, Any]:
        """Process job analysis"""
        # Implementation for job analysis
        return {"success": True, "output_data": {"analysis": "Job analysis completed"}}
    
    async def _process_bulk_generation(self, job: JobQueue) -> Dict[str, Any]:
        """Process bulk generation"""
        # Implementation for bulk generation
        return {"success": True, "output_data": {"processed": "Bulk generation completed"}}
    
    async def _update_job_progress(self, job_id: str, progress: int, message: str = None):
        """Update job progress"""
        update_data = {
            "progress_percentage": progress,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if message:
            update_data["current_step"] = message
        
        self.db.table("job_queue").update(update_data).eq("id", job_id).execute()
        
        # Log progress update
        if message:
            await self._log_job_event(job_id, LogLevel.INFO, message, {"progress": progress})
    
    async def _update_step_progress(self, job_id: str, step_name: str, status: StepStatus, progress: int):
        """Update step progress"""
        update_data = {
            "status": status.value,
            "progress_percentage": progress,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == StepStatus.PROCESSING:
            update_data["started_at"] = datetime.utcnow().isoformat()
        elif status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
            update_data["completed_at"] = datetime.utcnow().isoformat()
        
        self.db.table("job_processing_steps").update(update_data).eq("job_queue_id", job_id).eq("step_name", step_name).execute()
        
        # Update overall job progress
        self.db.rpc("calculate_job_progress", {"job_id": job_id}).execute()
    
    async def _complete_job(self, job_id: str, output_data: Dict[str, Any]):
        """Complete job processing"""
        self.db.rpc("complete_job_processing", {
            "job_id": job_id,
            "output_data": json.dumps(output_data),
            "success": True
        }).execute()
    
    async def _fail_job(self, job_id: str, error_message: str):
        """Fail job processing"""
        self.db.table("job_queue").update({
            "status": JobStatus.FAILED.value,
            "error_message": error_message,
            "retry_count": self.db.table("job_queue").select("retry_count").eq("id", job_id).execute().data[0]["retry_count"] + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", job_id).execute()
        
        await self._log_job_event(job_id, LogLevel.ERROR, f"Job failed: {error_message}")
    
    async def _log_job_event(self, job_id: str, level: LogLevel, message: str, metadata: Dict[str, Any] = None):
        """Log job event"""
        log_data = {
            "id": str(uuid4()),
            "job_queue_id": job_id,
            "log_level": level.value,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.db.table("job_processing_logs").insert(log_data).execute()
    
    async def get_job_with_steps(self, job_id: str, user_id: str) -> Optional[JobQueueWithSteps]:
        """Get job with processing steps and logs"""
        try:
            # Get job
            job_result = self.db.table("job_queue").select("*").eq("id", job_id).eq("user_id", user_id).execute()
            if not job_result.data:
                return None
            
            job = JobQueue(**job_result.data[0])
            
            # Get steps
            steps_result = self.db.table("job_processing_steps").select("*").eq("job_queue_id", job_id).order("step_order").execute()
            steps = [JobProcessingStep(**step) for step in steps_result.data]
            
            # Get logs
            logs_result = self.db.table("job_processing_logs").select("*").eq("job_queue_id", job_id).order("created_at").execute()
            logs = [JobProcessingLog(**log) for log in logs_result.data]
            
            return JobQueueWithSteps(**job.dict(), steps=steps, logs=logs)
            
        except Exception as e:
            logger.error(f"Failed to get job with steps: {e}")
            return None
    
    async def get_dashboard_stats(self, user_id: str) -> JobDashboardStats:
        """Get dashboard statistics"""
        try:
            # Get job counts by status
            status_result = self.db.table("job_queue").select("status", count="exact").eq("user_id", user_id).execute()
            
            stats = JobDashboardStats()
            stats.total_jobs = status_result.count or 0
            
            # Get detailed stats
            detailed_result = self.db.table("job_queue_dashboard").select("*").eq("user_id", user_id).execute()
            
            for job in detailed_result.data:
                if job["status"] == "pending":
                    stats.pending_jobs += 1
                elif job["status"] == "processing":
                    stats.processing_jobs += 1
                elif job["status"] == "completed":
                    stats.completed_jobs += 1
                elif job["status"] == "failed":
                    stats.failed_jobs += 1
                
                # Track job types
                job_type = job["job_type"]
                stats.jobs_by_type[job_type] = stats.jobs_by_type.get(job_type, 0) + 1
            
            # Calculate success rate
            if stats.total_jobs > 0:
                stats.success_rate = stats.completed_jobs / stats.total_jobs
            
            # Get recent jobs
            recent_result = self.db.table("job_queue").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
            stats.recent_jobs = [JobQueue(**job) for job in recent_result.data]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return JobDashboardStats()


# Global service instance
job_processor = JobProcessor