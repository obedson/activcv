"""
Job processing API endpoints for real-time job management
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from supabase import Client
import json
import asyncio

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.job_processor import JobProcessor
from app.models.job_processing import (
    JobQueue, JobQueueCreate, JobQueueUpdate, JobQueueWithSteps,
    JobType, JobStatus, JobDashboardStats, JobSearchFilters,
    JobRetryRequest, JobCancellationRequest, BulkJobRequest, BulkJobResponse,
    JobProgressUpdate
)

router = APIRouter()


def get_job_processor(db: Client = Depends(get_db)) -> JobProcessor:
    """Get job processor instance"""
    return JobProcessor(db)


@router.post("/", response_model=JobQueue)
async def create_job(
    job_create: JobQueueCreate,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    processor: JobProcessor = Depends(get_job_processor)
):
    """Create a new job in the processing queue"""
    try:
        # Set user_id from current user
        job_create.user_id = current_user
        
        # Create job
        job = await processor.create_job(job_create)
        
        # Add background task to process job
        background_tasks.add_task(_process_job_background, processor, job)
        
        return job
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/", response_model=List[JobQueue])
async def get_jobs(
    filters: JobSearchFilters = Depends(),
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get user's jobs with filtering"""
    try:
        query = db.table("job_queue").select("*").eq("user_id", current_user)
        
        # Apply filters
        if filters.job_type:
            query = query.eq("job_type", filters.job_type.value)
        
        if filters.status:
            query = query.eq("status", filters.status.value)
        
        if filters.date_from:
            query = query.gte("created_at", filters.date_from.isoformat())
        
        if filters.date_to:
            query = query.lte("created_at", filters.date_to.isoformat())
        
        if filters.priority_min:
            query = query.gte("priority", filters.priority_min)
        
        if filters.priority_max:
            query = query.lte("priority", filters.priority_max)
        
        # Order and paginate
        query = query.order("created_at", desc=True).range(filters.offset, filters.offset + filters.limit - 1)
        
        result = query.execute()
        
        return [JobQueue(**job) for job in result.data]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve jobs: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobQueueWithSteps)
async def get_job(
    job_id: str,
    current_user: str = Depends(get_current_user),
    processor: JobProcessor = Depends(get_job_processor)
):
    """Get specific job with processing steps and logs"""
    try:
        job = await processor.get_job_with_steps(job_id, current_user)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job: {str(e)}"
        )


@router.put("/{job_id}", response_model=JobQueue)
async def update_job(
    job_id: str,
    job_update: JobQueueUpdate,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Update job details"""
    try:
        # Verify ownership
        job_result = db.table("job_queue").select("id").eq("id", job_id).eq("user_id", current_user).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Update job
        update_data = {k: v for k, v in job_update.dict().items() if v is not None}
        if update_data:
            update_data["updated_at"] = "now()"
            result = db.table("job_queue").update(update_data).eq("id", job_id).execute()
            
            if result.data:
                return JobQueue(**result.data[0])
        
        # Return current job if no updates
        current_result = db.table("job_queue").select("*").eq("id", job_id).execute()
        return JobQueue(**current_result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job: {str(e)}"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Delete job (only if not processing)"""
    try:
        # Check job status
        job_result = db.table("job_queue").select("status").eq("id", job_id).eq("user_id", current_user).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job_status = job_result.data[0]["status"]
        if job_status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete job that is currently processing"
            )
        
        # Delete job (cascade will handle steps and logs)
        db.table("job_queue").delete().eq("id", job_id).execute()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )


@router.post("/{job_id}/retry", response_model=JobQueue)
async def retry_job(
    job_id: str,
    retry_request: JobRetryRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    processor: JobProcessor = Depends(get_job_processor),
    db: Client = Depends(get_db)
):
    """Retry a failed job"""
    try:
        # Verify ownership and status
        job_result = db.table("job_queue").select("*").eq("id", job_id).eq("user_id", current_user).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job = JobQueue(**job_result.data[0])
        
        if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed or cancelled jobs can be retried"
            )
        
        # Update job for retry
        update_data = {
            "status": JobStatus.PENDING.value,
            "error_message": None,
            "progress_percentage": 0,
            "current_step": None,
            "started_at": None,
            "completed_at": None,
            "updated_at": "now()"
        }
        
        if retry_request.reset_retry_count:
            update_data["retry_count"] = 0
        
        if retry_request.new_priority:
            update_data["priority"] = retry_request.new_priority
        
        if retry_request.scheduled_at:
            update_data["scheduled_at"] = retry_request.scheduled_at.isoformat()
        
        result = db.table("job_queue").update(update_data).eq("id", job_id).execute()
        
        if result.data:
            updated_job = JobQueue(**result.data[0])
            
            # Reset processing steps
            db.table("job_processing_steps").update({
                "status": "pending",
                "progress_percentage": 0,
                "error_message": None,
                "started_at": None,
                "completed_at": None,
                "updated_at": "now()"
            }).eq("job_queue_id", job_id).execute()
            
            # Add background task to process job
            background_tasks.add_task(_process_job_background, processor, updated_job)
            
            return updated_job
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry job"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )


@router.post("/{job_id}/cancel", response_model=JobQueue)
async def cancel_job(
    job_id: str,
    cancellation_request: JobCancellationRequest,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Cancel a pending or processing job"""
    try:
        # Verify ownership
        job_result = db.table("job_queue").select("status").eq("id", job_id).eq("user_id", current_user).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job_status = job_result.data[0]["status"]
        
        if job_status not in ["pending", "processing"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending or processing jobs can be cancelled"
            )
        
        # Cancel job
        update_data = {
            "status": JobStatus.CANCELLED.value,
            "error_message": cancellation_request.reason or "Job cancelled by user",
            "completed_at": "now()",
            "updated_at": "now()"
        }
        
        result = db.table("job_queue").update(update_data).eq("id", job_id).execute()
        
        if result.data:
            return JobQueue(**result.data[0])
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.post("/bulk", response_model=BulkJobResponse)
async def create_bulk_jobs(
    bulk_request: BulkJobRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    processor: JobProcessor = Depends(get_job_processor)
):
    """Create multiple jobs in bulk"""
    try:
        created_jobs = []
        failed_jobs = []
        
        for i, job_data in enumerate(bulk_request.jobs):
            try:
                job_create = JobQueueCreate(
                    user_id=current_user,
                    job_type=bulk_request.job_type,
                    priority=bulk_request.priority,
                    input_data=job_data,
                    max_retries=bulk_request.max_retries
                )
                
                job = await processor.create_job(job_create)
                created_jobs.append(job.id)
                
                # Add background task to process job
                background_tasks.add_task(_process_job_background, processor, job)
                
            except Exception as e:
                failed_jobs.append({
                    "index": str(i),
                    "error": str(e)
                })
        
        return BulkJobResponse(
            success=len(failed_jobs) == 0,
            total_jobs=len(bulk_request.jobs),
            created_jobs=created_jobs,
            failed_jobs=failed_jobs,
            batch_id=f"batch_{len(created_jobs)}_{current_user[:8]}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk jobs: {str(e)}"
        )


@router.get("/stats/dashboard", response_model=JobDashboardStats)
async def get_dashboard_stats(
    current_user: str = Depends(get_current_user),
    processor: JobProcessor = Depends(get_job_processor)
):
    """Get job processing dashboard statistics"""
    try:
        stats = await processor.get_dashboard_stats(current_user)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )


@router.websocket("/ws/{job_id}")
async def job_progress_websocket(
    websocket: WebSocket,
    job_id: str,
    current_user: str = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """WebSocket endpoint for real-time job progress updates"""
    await websocket.accept()
    
    try:
        # Verify job ownership
        job_result = db.table("job_queue").select("id").eq("id", job_id).eq("user_id", current_user).execute()
        
        if not job_result.data:
            await websocket.send_text(json.dumps({
                "error": "Job not found or access denied"
            }))
            await websocket.close()
            return
        
        # Subscribe to job updates
        while True:
            try:
                # Get current job status
                current_job = db.table("job_queue").select("*").eq("id", job_id).execute()
                
                if current_job.data:
                    job_data = current_job.data[0]
                    
                    progress_update = JobProgressUpdate(
                        job_id=job_id,
                        status=JobStatus(job_data["status"]),
                        progress_percentage=job_data["progress_percentage"],
                        current_step=job_data.get("current_step"),
                        updated_at=job_data["updated_at"]
                    )
                    
                    await websocket.send_text(progress_update.json())
                    
                    # Close connection if job is completed or failed
                    if job_data["status"] in ["completed", "failed", "cancelled"]:
                        break
                
                # Wait before next update
                await asyncio.sleep(2)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "error": f"Update error: {str(e)}"
                }))
                break
    
    except Exception as e:
        await websocket.send_text(json.dumps({
            "error": f"Connection error: {str(e)}"
        }))
    finally:
        await websocket.close()


# Background task functions

async def _process_job_background(processor: JobProcessor, job: JobQueue):
    """Background task for processing jobs"""
    try:
        await processor.process_job(job)
    except Exception as e:
        # Log error but don't raise to avoid breaking background task
        print(f"Background job processing failed: {e}")


# Job queue worker (can be run as separate process)
async def job_queue_worker(processor: JobProcessor):
    """Continuous job queue worker"""
    while True:
        try:
            # Get next job
            job = await processor.get_next_job()
            
            if job:
                # Process job
                await processor.process_job(job)
            else:
                # No jobs available, wait before checking again
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"Job queue worker error: {e}")
            await asyncio.sleep(10)  # Wait longer on error