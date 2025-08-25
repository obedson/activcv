"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from supabase import Client

from app.core.config import settings
from app.services.crew_agents import CrewAIService
from app.services.job_processor import JobProcessor
from app.services.document_vault import DocumentVaultService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock Supabase client"""
    mock_client = Mock(spec=Client)
    
    # Mock table operations
    mock_table = Mock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[])
    
    mock_client.table.return_value = mock_table
    mock_client.rpc.return_value = Mock(execute=Mock(return_value=Mock(data=[])))
    
    return mock_client


@pytest.fixture
def mock_crew_service():
    """Mock CrewAI service"""
    service = Mock(spec=CrewAIService)
    service.process_cv_generation = AsyncMock(return_value={
        "success": True,
        "generated_content": {"summary": "Test summary"},
        "metadata": {"template": "modern_one_page"}
    })
    service.generate_cover_letter = AsyncMock(return_value={
        "success": True,
        "cover_letter_content": "Test cover letter content",
        "metadata": {"template": "professional"}
    })
    return service


@pytest.fixture
def job_processor(mock_db):
    """Job processor instance with mocked dependencies"""
    return JobProcessor(mock_db)


@pytest.fixture
def document_vault_service(mock_db):
    """Document vault service with mocked dependencies"""
    return DocumentVaultService(mock_db)


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing"""
    return {
        "user_id": "test-user-123",
        "full_name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "location": "New York, NY",
        "summary": "Experienced software developer",
        "experience": [
            {
                "id": "exp1",
                "job_title": "Senior Developer",
                "company": "Tech Corp",
                "start_date": "2020-01-01",
                "end_date": "2023-12-31",
                "description": "Led development team"
            }
        ],
        "education": [
            {
                "id": "edu1",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "institution": "University of Technology",
                "graduation_date": "2019-05-01"
            }
        ],
        "skills": [
            {"id": "skill1", "skill_name": "Python", "proficiency_level": "Advanced"},
            {"id": "skill2", "skill_name": "JavaScript", "proficiency_level": "Intermediate"}
        ]
    }


@pytest.fixture
def sample_job():
    """Sample job for testing"""
    return {
        "id": "job-123",
        "title": "Senior Software Engineer",
        "company": "Example Corp",
        "location": "San Francisco, CA",
        "description": "We are looking for a senior software engineer with Python experience",
        "requirements": "5+ years Python, React, AWS experience required",
        "salary_range": "$120,000 - $150,000",
        "job_type": "full_time",
        "work_mode": "hybrid",
        "posted_date": "2024-01-15",
        "application_deadline": "2024-02-15"
    }


@pytest.fixture
def sample_job_queue_item():
    """Sample job queue item for testing"""
    return {
        "id": "queue-123",
        "user_id": "test-user-123",
        "job_type": "cv_generation",
        "status": "pending",
        "priority": 5,
        "input_data": {
            "template": "modern_one_page",
            "job_id": "job-123"
        },
        "progress_percentage": 0,
        "total_steps": 7,
        "retry_count": 0,
        "max_retries": 3
    }


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        "id": "doc-123",
        "user_id": "test-user-123",
        "document_type": "cv",
        "title": "Senior Software Engineer CV",
        "description": "CV for tech position",
        "file_name": "cv_senior_engineer.pdf",
        "file_path": "/documents/test-user-123/cv/cv_senior_engineer.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "template_used": "modern_one_page",
        "status": "active"
    }


# Test data constants
TEST_USER_ID = "test-user-123"
TEST_JOB_ID = "job-123"
TEST_DOCUMENT_ID = "doc-123"