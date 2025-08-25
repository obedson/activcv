"""
Tests for document vault system
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from app.services.document_vault import DocumentVaultService


class TestDocumentVaultService:
    """Test document vault functionality"""
    
    @pytest.mark.asyncio
    async def test_store_document(self, document_vault_service, mock_db):
        """Test document storage"""
        # Setup
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Test PDF content")
            temp_file_path = temp_file.name
        
        try:
            # Mock storage service
            with patch('app.services.document_vault.storage_service') as mock_storage:
                mock_storage.upload_file = AsyncMock(return_value={
                    "success": True,
                    "file_path": "/documents/test-user/cv/test.pdf",
                    "public_url": "https://example.com/test.pdf"
                })
                
                # Mock database response
                mock_db.table.return_value.insert.return_value.execute.return_value = Mock(
                    data=[{
                        "id": "doc-123",
                        "user_id": "test-user-123",
                        "document_type": "cv",
                        "title": "Test CV",
                        "file_name": "test.pdf",
                        "file_path": "/documents/test-user/cv/test.pdf",
                        "file_url": "https://example.com/test.pdf",
                        "file_size": 16,
                        "status": "active"
                    }]
                )
                
                # Execute
                result = await document_vault_service.store_document(
                    user_id="test-user-123",
                    file_path=temp_file_path,
                    document_type="cv",
                    title="Test CV"
                )
        
        finally:
            # Cleanup
            os.unlink(temp_file_path)
        
        # Assert
        assert result["success"] is True
        assert result["document"]["id"] == "doc-123"
        assert result["document"]["title"] == "Test CV"
    
    @pytest.mark.asyncio
    async def test_store_document_duplicate_detection(self, document_vault_service, mock_db):
        """Test duplicate document detection"""
        # Setup
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Test PDF content")
            temp_file_path = temp_file.name
        
        try:
            # Mock existing document
            with patch.object(document_vault_service, '_check_duplicate', return_value={"id": "existing-doc"}):
                # Execute
                result = await document_vault_service.store_document(
                    user_id="test-user-123",
                    file_path=temp_file_path,
                    document_type="cv",
                    title="Test CV"
                )
        
        finally:
            os.unlink(temp_file_path)
        
        # Assert
        assert result["success"] is False
        assert "Duplicate document" in result["error"]
        assert result["existing_document_id"] == "existing-doc"
    
    @pytest.mark.asyncio
    async def test_get_documents(self, document_vault_service, mock_db):
        """Test document retrieval with filtering"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = Mock(
            data=[
                {
                    "id": "doc-1",
                    "title": "CV 1",
                    "document_type": "cv",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "doc-2",
                    "title": "Cover Letter 1",
                    "document_type": "cover_letter",
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ]
        )
        
        # Execute
        result = await document_vault_service.get_documents(
            user_id="test-user-123",
            document_type="cv",
            limit=10
        )
        
        # Assert
        assert result["success"] is True
        assert len(result["documents"]) == 2
        assert result["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_document(self, document_vault_service, mock_db):
        """Test single document retrieval"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                "id": "doc-123",
                "title": "Test Document",
                "user_id": "test-user-123",
                "document_type": "cv"
            }]
        )
        
        # Execute
        result = await document_vault_service.get_document("doc-123", "test-user-123")
        
        # Assert
        assert result is not None
        assert result["id"] == "doc-123"
        assert result["title"] == "Test Document"
    
    @pytest.mark.asyncio
    async def test_update_document(self, document_vault_service, mock_db):
        """Test document metadata update"""
        # Setup
        # Mock get_document
        with patch.object(document_vault_service, 'get_document', return_value={"id": "doc-123"}):
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
                data=[{
                    "id": "doc-123",
                    "title": "Updated Title",
                    "description": "Updated description"
                }]
            )
            
            # Execute
            result = await document_vault_service.update_document(
                document_id="doc-123",
                user_id="test-user-123",
                updates={"title": "Updated Title", "description": "Updated description"}
            )
        
        # Assert
        assert result["success"] is True
        assert result["document"]["title"] == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_delete_document_archive(self, document_vault_service, mock_db):
        """Test document archiving (soft delete)"""
        # Setup
        with patch.object(document_vault_service, 'get_document', return_value={"id": "doc-123"}):
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
                data=[{"id": "doc-123", "status": "deleted"}]
            )
            
            # Execute
            result = await document_vault_service.delete_document(
                document_id="doc-123",
                user_id="test-user-123",
                permanent=False
            )
        
        # Assert
        assert result["success"] is True
        assert "archived" in result["message"]
    
    @pytest.mark.asyncio
    async def test_delete_document_permanent(self, document_vault_service, mock_db):
        """Test permanent document deletion"""
        # Setup
        with patch.object(document_vault_service, 'get_document', return_value={
            "id": "doc-123",
            "file_path": "/documents/test.pdf"
        }):
            with patch('app.services.document_vault.storage_service') as mock_storage:
                mock_storage.delete_file = AsyncMock(return_value=True)
                
                # Execute
                result = await document_vault_service.delete_document(
                    document_id="doc-123",
                    user_id="test-user-123",
                    permanent=True
                )
        
        # Assert
        assert result["success"] is True
        assert "permanently deleted" in result["message"]
        mock_storage.delete_file.assert_called_once_with("/documents/test.pdf")
    
    @pytest.mark.asyncio
    async def test_create_share_link(self, document_vault_service, mock_db):
        """Test share link creation"""
        # Setup
        with patch.object(document_vault_service, 'get_document', return_value={"id": "doc-123"}):
            mock_db.table.return_value.insert.return_value.execute.return_value = Mock(
                data=[{
                    "id": "share-123",
                    "document_id": "doc-123",
                    "share_token": "abc123token",
                    "permissions": ["view"]
                }]
            )
            
            # Execute
            result = await document_vault_service.create_share_link(
                document_id="doc-123",
                user_id="test-user-123",
                permissions=["view"],
                expires_in_days=7
            )
        
        # Assert
        assert result["success"] is True
        assert "share_url" in result
        assert "share_token" in result
        assert result["share_token"] == "abc123token"
    
    @pytest.mark.asyncio
    async def test_get_shared_document(self, document_vault_service, mock_db):
        """Test shared document access"""
        # Setup
        # Mock share info
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                "id": "share-123",
                "document_id": "doc-123",
                "permissions": ["view"],
                "access_count": 0,
                "expires_at": None
            }]
        )
        
        # Mock document
        def mock_table_side_effect(table_name):
            if table_name == "document_shares":
                mock_table = Mock()
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
                    data=[{
                        "id": "share-123",
                        "document_id": "doc-123",
                        "permissions": ["view"],
                        "access_count": 0,
                        "expires_at": None
                    }]
                )
                mock_table.update.return_value.eq.return_value.execute.return_value = Mock()
                return mock_table
            elif table_name == "document_vault":
                mock_table = Mock()
                mock_table.select.return_value.eq.return_value.execute.return_value = Mock(
                    data=[{
                        "id": "doc-123",
                        "title": "Shared Document",
                        "document_type": "cv"
                    }]
                )
                return mock_table
        
        mock_db.table.side_effect = mock_table_side_effect
        
        # Execute
        result = await document_vault_service.get_shared_document("abc123token")
        
        # Assert
        assert result is not None
        assert result["id"] == "doc-123"
        assert result["share_permissions"] == ["view"]
    
    @pytest.mark.asyncio
    async def test_get_folders(self, document_vault_service, mock_db):
        """Test folder retrieval"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[
                {"id": "folder-1", "name": "CVs", "color": "#10B981"},
                {"id": "folder-2", "name": "Cover Letters", "color": "#3B82F6"}
            ]
        )
        
        # Execute
        result = await document_vault_service.get_folders("test-user-123")
        
        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "CVs"
        assert result[1]["name"] == "Cover Letters"
    
    @pytest.mark.asyncio
    async def test_create_folder(self, document_vault_service, mock_db):
        """Test folder creation"""
        # Setup
        mock_db.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{
                "id": "folder-123",
                "name": "New Folder",
                "user_id": "test-user-123",
                "color": "#3B82F6"
            }]
        )
        
        # Execute
        result = await document_vault_service.create_folder(
            user_id="test-user-123",
            name="New Folder",
            description="Test folder"
        )
        
        # Assert
        assert result["success"] is True
        assert result["folder"]["name"] == "New Folder"
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, document_vault_service, mock_db):
        """Test storage statistics"""
        # Setup
        mock_db.rpc.return_value.execute.return_value = Mock(
            data=[{
                "total_documents": 25,
                "total_size_bytes": 52428800,  # 50MB
                "storage_used_mb": 50.0,
                "documents_by_type": {"cv": 15, "cover_letter": 10}
            }]
        )
        
        # Execute
        result = await document_vault_service.get_storage_stats("test-user-123")
        
        # Assert
        assert result["success"] is True
        stats = result["stats"]
        assert stats["total_documents"] == 25
        assert stats["storage_used_mb"] == 50.0
        assert stats["storage_used_percentage"] == 5.0  # 50MB / 1000MB * 100
    
    @pytest.mark.asyncio
    async def test_create_system_folders(self, document_vault_service, mock_db):
        """Test system folder creation"""
        # Setup
        mock_db.rpc.return_value.execute.return_value = Mock()
        
        # Execute
        result = await document_vault_service.create_system_folders("test-user-123")
        
        # Assert
        assert result["success"] is True
        mock_db.rpc.assert_called_with("create_system_folders_for_user", {"user_id": "test-user-123"})


class TestDocumentVaultHelpers:
    """Test document vault helper methods"""
    
    def test_get_file_info(self, document_vault_service):
        """Test file information extraction"""
        # Setup
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Test PDF content")
            temp_file_path = temp_file.name
        
        try:
            # Execute
            file_info = document_vault_service._get_file_info(temp_file_path)
            
            # Assert
            assert file_info["name"] == Path(temp_file_path).name
            assert file_info["size"] == 16  # Length of "Test PDF content"
            assert file_info["mime_type"] == "application/pdf"
            assert "hash" in file_info
            assert len(file_info["hash"]) == 64  # SHA256 hash length
        
        finally:
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_check_duplicate(self, document_vault_service, mock_db):
        """Test duplicate file detection"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "existing-doc", "title": "Existing Document"}]
        )
        
        # Execute
        result = await document_vault_service._check_duplicate("test-user-123", "test-hash")
        
        # Assert
        assert result is not None
        assert result["id"] == "existing-doc"
    
    @pytest.mark.asyncio
    async def test_get_default_folder(self, document_vault_service, mock_db):
        """Test default folder retrieval"""
        # Setup
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "cv-folder-123"}]
        )
        
        # Execute
        result = await document_vault_service._get_default_folder("test-user-123", "cv")
        
        # Assert
        assert result == "cv-folder-123"
    
    def test_generate_share_token(self, document_vault_service):
        """Test share token generation"""
        # Execute
        token = document_vault_service._generate_share_token()
        
        # Assert
        assert isinstance(token, str)
        assert len(token) == 32
        assert token.isalnum()  # Should be alphanumeric