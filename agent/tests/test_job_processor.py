"""
Tests for job processing system
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.job_processor import JobProcessor
from app.models.job_processing import JobQueue, JobQueueCreate, JobType, JobStatus


class TestJobProcessor:
    """Test job processing functionality"""
    
    @pytest.mark.asyncio
    async def test_create_job(self, job_processor, mock_db):
        """Test job creation"""
        # Setup
        job_create = JobQueueCreate(
            user_id="test-user-123",
            job_type=JobType.CV_GENERATION,
            input_data={"template": "modern_one_page"}
        )
        
        # Mock database response
        mock_db.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{
                "id": "job-123",
                "user_id": "test-user-123",
                "job_type": "cv_generation",
                "status": "pending",
                "priority": 5,
                "input_data": {"template": "modern_one_page"},
                "progress_percentage": 0,
                "total_steps": 1,
                "created_at": datetime.utcnow().isoformat()
            }]
        )
        
        # Execute
        result = await job_processor.create_job(job_create)
        
        # Assert
        assert isinstance(result, JobQueue)
        assert result.user_id == "test-user-123"
        assert result.job_type == JobType.CV_GENERATION
        assert result.status == JobStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_get_next_job(self, job_processor, mock_db):
        """Test getting next job from queue"""
        # Setup
        mock_db.rpc.return_value.execute.return_value = Mock(
            data=[{
                "job_id": "job-123",
                "user_id": "test-user-123",
                "job_type": "cv_generation",
                "input_data": {"template": "modern_one_page"},
                "priority": 5
            }]
        )
        
        # Execute
        result = await job_processor.get_next_job()
        
        # Assert
        assert result is not None
        assert result.id == "job-123"
        assert result.job_type == JobType.CV_GENERATION
    
    @pytest.mark.asyncio
    async def test_start_job_processing(self, job_processor, mock_db):
        """Test starting job processing"""
        # Setup
        job_id = "job-123"
        mock_db.rpc.return_value.execute.return_value = Mock(data=True)
        
        # Execute
        result = await job_processor.start_job_processing(job_id)
        
        # Assert
        assert result is True
        mock_db.rpc.assert_called_with("start_job_processing", {"job_id": job_id})
    
    @pytest.mark.asyncio
    async def test_update_job_progress(self, job_processor, mock_db):
        """Test updating job progress"""
        # Setup
        job_id = "job-123"
        progress = 50
        message = "Processing step 3"
        
        # Execute
        await job_processor._update_job_progress(job_id, progress, message)
        
        # Assert
        mock_db.table.assert_called_with("job_queue")
        update_call = mock_db.table.return_value.update
        assert update_call.called
    
    @pytest.mark.asyncio
    async def test_process_cv_generation_job(self, job_processor, sample_job_queue_item, mock_crew_service):
        """Test CV generation job processing"""
        # Setup
        job = JobQueue(**sample_job_queue_item)
        job.job_type = JobType.CV_GENERATION
        
        with patch('app.services.job_processor.crew_service', mock_crew_service):
            with patch('app.services.job_processor.cv_generator') as mock_cv_gen:
                mock_cv_gen.apply_template = AsyncMock(return_value={"html_content": "<html>CV</html>"})
                mock_cv_gen.generate_pdf = AsyncMock(return_value={
                    "pdf_url": "https://example.com/cv.pdf",
                    "file_size": 1024000
                })
                
                with patch('app.services.job_processor.email_service') as mock_email:
                    mock_email.send_cv_ready_notification = AsyncMock(return_value=True)
                    
                    # Execute
                    result = await job_processor._process_cv_generation(job)
        
        # Assert
        assert result["success"] is True
        assert "output_data" in result
        assert result["output_data"]["cv_url"] == "https://example.com/cv.pdf"
    
    @pytest.mark.asyncio
    async def test_process_cover_letter_generation_job(self, job_processor, sample_job_queue_item, mock_crew_service):
        """Test cover letter generation job processing"""
        # Setup
        job = JobQueue(**sample_job_queue_item)
        job.job_type = JobType.COVER_LETTER_GENERATION
        job.input_data = {"job_id": "job-123", "template_key": "professional"}
        
        with patch('app.services.job_processor.crew_service', mock_crew_service):
            with patch('app.services.job_processor.cover_letter_generator') as mock_cl_gen:
                mock_cl_gen.apply_template = AsyncMock(return_value={"html_content": "<html>Cover Letter</html>"})
                mock_cl_gen.generate_pdf = AsyncMock(return_value={
                    "pdf_url": "https://example.com/cover_letter.pdf",
                    "file_size": 512000
                })
                
                with patch('app.services.job_processor.email_service') as mock_email:
                    mock_email.send_cover_letter_ready_notification = AsyncMock(return_value=True)
                    
                    # Execute
                    result = await job_processor._process_cover_letter_generation(job)
        
        # Assert
        assert result["success"] is True
        assert "output_data" in result
        assert result["output_data"]["cover_letter_url"] == "https://example.com/cover_letter.pdf"
    
    @pytest.mark.asyncio
    async def test_complete_job(self, job_processor, mock_db):
        """Test job completion"""
        # Setup
        job_id = "job-123"
        output_data = {"result": "success"}
        
        # Execute
        await job_processor._complete_job(job_id, output_data)
        
        # Assert
        mock_db.rpc.assert_called_with("complete_job_processing", {
            "job_id": job_id,
            "output_data": '{"result": "success"}',
            "success": True
        })
    
    @pytest.mark.asyncio
    async def test_fail_job(self, job_processor, mock_db):
        """Test job failure handling"""
        # Setup
        job_id = "job-123"
        error_message = "Processing failed"
        
        # Mock current retry count
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"retry_count": 1}]
        )
        
        # Execute
        await job_processor._fail_job(job_id, error_message)
        
        # Assert
        update_call = mock_db.table.return_value.update
        assert update_call.called
        update_args = update_call.call_args[0][0]
        assert update_args["status"] == JobStatus.FAILED.value
        assert update_args["error_message"] == error_message
    
    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, job_processor, mock_db):
        """Test dashboard statistics retrieval"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            count=10
        )
        
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
            data=[
                {
                    "id": "job-1",
                    "job_type": "cv_generation",
                    "status": "completed",
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        )
        
        # Execute
        result = await job_processor.get_dashboard_stats("test-user-123")
        
        # Assert
        assert result.total_jobs == 10
        assert len(result.recent_jobs) == 1
        assert result.recent_jobs[0].job_type == JobType.CV_GENERATION


class TestJobProcessingSteps:
    """Test job processing step management"""
    
    @pytest.mark.asyncio
    async def test_update_step_progress(self, job_processor, mock_db):
        """Test updating step progress"""
        # Setup
        job_id = "job-123"
        step_name = "profile_analysis"
        status = "processing"
        progress = 50
        
        # Execute
        await job_processor._update_step_progress(job_id, step_name, status, progress)
        
        # Assert
        mock_db.table.assert_called_with("job_processing_steps")
        update_call = mock_db.table.return_value.update
        assert update_call.called
    
    @pytest.mark.asyncio
    async def test_log_job_event(self, job_processor, mock_db):
        """Test job event logging"""
        # Setup
        job_id = "job-123"
        level = "info"
        message = "Job started"
        metadata = {"step": "initialization"}
        
        # Execute
        await job_processor._log_job_event(job_id, level, message, metadata)
        
        # Assert
        mock_db.table.assert_called_with("job_processing_logs")
        insert_call = mock_db.table.return_value.insert
        assert insert_call.called


class TestJobProcessingIntegration:
    """Integration tests for job processing"""
    
    @pytest.mark.asyncio
    async def test_full_job_processing_workflow(self, job_processor, sample_job_queue_item, mock_crew_service):
        """Test complete job processing workflow"""
        # Setup
        job = JobQueue(**sample_job_queue_item)
        
        with patch.multiple(
            job_processor,
            start_job_processing=AsyncMock(return_value=True),
            _process_cv_generation=AsyncMock(return_value={"success": True, "output_data": {}}),
            _complete_job=AsyncMock(),
            _log_job_event=AsyncMock()
        ):
            # Execute
            result = await job_processor.process_job(job)
        
        # Assert
        assert result is True
        job_processor.start_job_processing.assert_called_once_with(job.id)
        job_processor._process_cv_generation.assert_called_once_with(job)
        job_processor._complete_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_job_processing_failure_handling(self, job_processor, sample_job_queue_item):
        """Test job processing failure handling"""
        # Setup
        job = JobQueue(**sample_job_queue_item)
        
        with patch.multiple(
            job_processor,
            start_job_processing=AsyncMock(return_value=True),
            _process_cv_generation=AsyncMock(side_effect=Exception("Processing failed")),
            _fail_job=AsyncMock(),
            _log_job_event=AsyncMock()
        ):
            # Execute
            result = await job_processor.process_job(job)
        
        # Assert
        assert result is False
        job_processor._fail_job.assert_called_once_with(job.id, "Processing failed")