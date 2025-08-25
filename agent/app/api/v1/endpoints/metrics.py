"""
Metrics and monitoring endpoints for Prometheus
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Response
from supabase import Client
from datetime import datetime, timedelta

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/metrics")
async def get_prometheus_metrics(db: Client = Depends(get_db)):
    """Prometheus metrics endpoint"""
    try:
        metrics = []
        
        # Job queue metrics
        job_stats = await _get_job_queue_metrics(db)
        metrics.extend([
            f"job_queue_pending_count {job_stats['pending']}",
            f"job_queue_processing_count {job_stats['processing']}",
            f"job_queue_completed_count {job_stats['completed']}",
            f"job_queue_failed_count {job_stats['failed']}",
            f"job_failures_total {job_stats['total_failures']}",
            f"job_success_rate {job_stats['success_rate']}"
        ])
        
        # Document vault metrics
        doc_stats = await _get_document_metrics(db)
        metrics.extend([
            f"document_vault_total_documents {doc_stats['total_documents']}",
            f"document_vault_total_size_bytes {doc_stats['total_size_bytes']}",
            f"document_storage_usage_percentage {doc_stats['storage_usage_percentage']}"
        ])
        
        # User metrics
        user_stats = await _get_user_metrics(db)
        metrics.extend([
            f"total_users {user_stats['total_users']}",
            f"active_users_24h {user_stats['active_24h']}",
            f"new_users_24h {user_stats['new_24h']}"
        ])
        
        # AI service metrics (mock for now)
        metrics.extend([
            "ai_service_health 1",
            "ai_service_response_time_seconds 2.5"
        ])
        
        # HTTP metrics (would be collected by middleware)
        metrics.extend([
            "http_requests_total 1000",
            "http_request_duration_seconds 0.5"
        ])
        
        metrics_text = "\n".join(metrics)
        
        return Response(
            content=metrics_text,
            media_type="text/plain"
        )
        
    except Exception as e:
        return Response(
            content=f"# Error collecting metrics: {str(e)}",
            media_type="text/plain",
            status_code=500
        )


@router.get("/jobs")
async def get_job_metrics(db: Client = Depends(get_db)):
    """Detailed job processing metrics"""
    try:
        # Get job statistics
        job_stats = await _get_detailed_job_metrics(db)
        
        return {
            "success": True,
            "metrics": job_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/documents")
async def get_document_metrics(db: Client = Depends(get_db)):
    """Detailed document vault metrics"""
    try:
        # Get document statistics
        doc_stats = await _get_detailed_document_metrics(db)
        
        return {
            "success": True,
            "metrics": doc_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/system")
async def get_system_metrics():
    """System health and performance metrics"""
    try:
        import psutil
        import os
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Process info
        process = psutil.Process(os.getpid())
        
        return {
            "success": True,
            "metrics": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_bytes": disk.total,
                    "free_bytes": disk.free,
                    "used_bytes": disk.used,
                    "usage_percent": (disk.used / disk.total) * 100
                },
                "process": {
                    "memory_bytes": process.memory_info().rss,
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files())
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Helper functions

async def _get_job_queue_metrics(db: Client) -> Dict[str, Any]:
    """Get job queue metrics"""
    try:
        # Get job counts by status
        result = db.table("job_queue").select("status", count="exact").execute()
        
        status_counts = {}
        for item in result.data:
            status = item.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_jobs = sum(status_counts.values())
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        
        success_rate = (completed / total_jobs) if total_jobs > 0 else 1.0
        
        return {
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": completed,
            "failed": failed,
            "total_failures": failed,
            "success_rate": success_rate
        }
        
    except Exception:
        return {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total_failures": 0,
            "success_rate": 1.0
        }


async def _get_document_metrics(db: Client) -> Dict[str, Any]:
    """Get document vault metrics"""
    try:
        # Get document counts and sizes
        result = db.table("document_vault").select("file_size", count="exact").eq("status", "active").execute()
        
        total_documents = result.count or 0
        total_size = sum(item.get("file_size", 0) for item in result.data if item.get("file_size"))
        
        # Calculate storage usage percentage (assuming 1GB limit per user)
        storage_limit = 1024 * 1024 * 1024  # 1GB in bytes
        storage_usage_percentage = (total_size / storage_limit) * 100 if storage_limit > 0 else 0
        
        return {
            "total_documents": total_documents,
            "total_size_bytes": total_size,
            "storage_usage_percentage": min(100, storage_usage_percentage)
        }
        
    except Exception:
        return {
            "total_documents": 0,
            "total_size_bytes": 0,
            "storage_usage_percentage": 0
        }


async def _get_user_metrics(db: Client) -> Dict[str, Any]:
    """Get user metrics"""
    try:
        # Get total users (from profiles table)
        total_result = db.table("profiles").select("user_id", count="exact").execute()
        total_users = total_result.count or 0
        
        # Get active users in last 24 hours (from job queue or document access)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_result = db.table("job_queue").select("user_id").gte("created_at", yesterday.isoformat()).execute()
        active_users = len(set(item["user_id"] for item in active_result.data if item.get("user_id")))
        
        # Get new users in last 24 hours
        new_result = db.table("profiles").select("user_id", count="exact").gte("created_at", yesterday.isoformat()).execute()
        new_users = new_result.count or 0
        
        return {
            "total_users": total_users,
            "active_24h": active_users,
            "new_24h": new_users
        }
        
    except Exception:
        return {
            "total_users": 0,
            "active_24h": 0,
            "new_24h": 0
        }


async def _get_detailed_job_metrics(db: Client) -> Dict[str, Any]:
    """Get detailed job processing metrics"""
    try:
        # Job processing times
        processing_result = db.table("job_queue_dashboard").select("*").execute()
        
        processing_times = []
        queue_wait_times = []
        
        for job in processing_result.data:
            if job.get("processing_time_ms"):
                processing_times.append(job["processing_time_ms"])
            if job.get("queue_wait_time_ms"):
                queue_wait_times.append(job["queue_wait_time_ms"])
        
        # Calculate averages
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        avg_queue_wait_time = sum(queue_wait_times) / len(queue_wait_times) if queue_wait_times else 0
        
        # Job types distribution
        job_types = {}
        for job in processing_result.data:
            job_type = job.get("job_type", "unknown")
            job_types[job_type] = job_types.get(job_type, 0) + 1
        
        return {
            "average_processing_time_ms": avg_processing_time,
            "average_queue_wait_time_ms": avg_queue_wait_time,
            "job_types_distribution": job_types,
            "total_jobs_processed": len(processing_result.data)
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "average_processing_time_ms": 0,
            "average_queue_wait_time_ms": 0,
            "job_types_distribution": {},
            "total_jobs_processed": 0
        }


async def _get_detailed_document_metrics(db: Client) -> Dict[str, Any]:
    """Get detailed document vault metrics"""
    try:
        # Document types distribution
        doc_result = db.table("document_vault").select("document_type, file_size").eq("status", "active").execute()
        
        doc_types = {}
        total_downloads = 0
        
        for doc in doc_result.data:
            doc_type = doc.get("document_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        # Get download statistics
        download_result = db.table("document_vault").select("download_count").eq("status", "active").execute()
        total_downloads = sum(item.get("download_count", 0) for item in download_result.data)
        
        # Get sharing statistics
        share_result = db.table("document_shares").select("document_id", count="exact").eq("is_active", True).execute()
        total_shares = share_result.count or 0
        
        return {
            "document_types_distribution": doc_types,
            "total_downloads": total_downloads,
            "total_active_shares": total_shares,
            "average_downloads_per_document": total_downloads / len(doc_result.data) if doc_result.data else 0
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "document_types_distribution": {},
            "total_downloads": 0,
            "total_active_shares": 0,
            "average_downloads_per_document": 0
        }